# Had to use the port 27018 cause the 17 wasn't working
docker run -d --name mongo-local -p 27018:27017 mongo:7

mongosh "mongodb://localhost:27018" --file DBScript.txt

# Then mongosh "mongodb://localhost:27018" and use cleanupDB to test