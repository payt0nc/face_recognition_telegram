docker run --rm --net face_recog_default \
  --link face_recog_mongo_1:mongo \
  -v "`pwd`/backup:/backup" mongo \
  bash -c 'mongorestore /backup --host mongo:27017'   
