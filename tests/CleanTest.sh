URI="mongodb://localhost:27017"

mongosh "$URI" --eval 'db.getSiblingDB("cleanupDB").dropDatabase()'

docker rm -f mongo-local

docker rmi mongo:7

docker volume prune
