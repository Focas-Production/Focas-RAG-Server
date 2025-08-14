# Use an official Node.js runtime as a parent image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy package.json AND package-lock.json
COPY package*.json ./

# Install app dependencies using npm with a longer timeout
RUN npm install --timeout=900000

# Copy the rest of the application code
COPY . .

# Make port 5555 available to the world outside this container
EXPOSE 5555

# Define the command to run your app
CMD [ "node", "server.js" ]