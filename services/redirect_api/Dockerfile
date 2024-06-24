# Use the official Node.js image as the base image
FROM node:22

# Create and change to the app directory
WORKDIR /app

# Copy the package.json and package-lock.json files
COPY package*.json .
COPY tsconfig.json .

# Install dependencies
RUN npm install

# Copy the rest of your application code
COPY ./src ./src

# Build the TypeScript code
RUN npm run build

# Expose the port your app runs on
EXPOSE 3000

# Define the command to run your app
CMD ["npm", "start"]