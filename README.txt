******README******
RABBITMQ INTERFACE
******************

This documentation describes how to use the RabbitMQ management interface and check
to see if queues are being created on the messaging side.

***********
***STEPS***
***********

1 - Start up the docker container and login to RabbitMQ on "localhost:15672"

2 - Click on "Queues" out of the 6 tabs on the page
	Using this page we're able to view a live feed of what events are coming through the
	RabbitMQ interface

3 - On a new tab, navigate to the website on "localhost:5000"
	We will generate some events in the messaging interface

4 - Create a user on the website and log in with the created user

5 - Quickly go back to your RabbitMQ interface and you should see the traffic spike up

***********
**RESULTS**
***********

From our spiked traffic, we can see that RabbitMQ is picking up events from our frontend.
Our backend is able to view these events and use the database to either create a user or 
login with a previously created one.
