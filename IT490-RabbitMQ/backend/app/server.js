#!/usr/bin/env node

const https = require('https')

// Messaging configuration
const messaging_host = 'messaging';
const messaging_user = process.env.MSG_USER;
const messaging_pass = process.env.MSG_PASS;
const queue = 'requests';
const messaging_url = `amqp://${messaging_user}:${messaging_pass}@${messaging_host}`;
const amqp = require('amqplib/callback_api');

// Database configuration
//const db_host = 'db';
//const db_user = process.env.DB_USER;
//const db_pass = process.env.DB_PASS;
//const db_database = process.env.DB_DATABASE;
//const mariadb = require('mariadb/callback');
//const db_pool = mariadb.createPool({host: db_host, user: db_user,
//  password: db_pass, database: db_database});

function send_response(channel, msg, response) {
  channel.sendToQueue(msg.properties.replyTo, Buffer.from(JSON.stringify(response)), {
    correlationId: msg.properties.correlationId
  });
  channel.ack(msg);
}

amqp.connect(messaging_url, function(error0, connection) {
  if (error0) {
    throw error0;
  }
  connection.createChannel(function(error1, channel) {
    if (error1) {
      throw error1;
    }
    channel.assertQueue(queue, {
      durable: false
    });
    channel.prefetch(1);
    console.log('Listening for requests...');
    channel.consume(queue, function reply(msg) {
      console.log(`Received: ${msg.content}`);
      var received_json = JSON.parse(msg.content);
      var action = received_json['action'];
      switch(action) {
        case 'ECHO':
          data = received_json['data'];
          console.log(`Echoing ${data}`);
          send_response(channel, msg, {'status': 'OK', 'data': data});
          break;
        case 'CARS':
          console.log('Returning a list of cars from the database');
          db_pool.getConnection((err, conn) => {
            if (err) {
              send_response(channel, msg, {'status': 'ERROR',
                'message': `Unable to connect to database: ${err}`});
            } else {
              conn.query("SELECT * FROM car", (err, rows) => {
                if (err) {
                  send_response(channel, msg, {'status': 'ERROR',
                    'message': `Unable to execute query: ${err}`});
                } else {
                  send_response(channel, msg, {'status': 'OK', 'data': rows});
                }
              });
              conn.end();
            }
          });
          break;
        case 'SCRAPE':
          var date = received_json['data'];
          console.log(`Returning a list of events from NJ.com for ${date}`);
          https.get(
            'https://www.nj.com/web/gateway.php?' +
            'affil=nj&site=default&hidemap=1&tpl=v3_regular_event_grid&' +
            `date=${date}`,
            (res) => {
              res.setEncoding('utf8');
              res.on('data', (body) => {
                var json_data = JSON.parse(body);
                send_response(channel, msg, json_data);
              });
              res.on('error', (error) => {
                send_response(channel, msg, error);
              });
            });
          break;
        default:
          console.log('Unknown action');
          send_response(channel, msg, {'status': 'ERROR', 'message': 'Unknown action'});
          break;
      }
    });
  });
});