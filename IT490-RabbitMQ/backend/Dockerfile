FROM node:12.16.2
COPY ./app/ /home/node/app
WORKDIR /home/node/app
RUN npm install
CMD sh -c 'sleep 30; npm start'