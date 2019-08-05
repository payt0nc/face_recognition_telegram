docker run --rm --net face_recog_default \
  --link face_recog_mongo_1:mongo \
  -v "`pwd`/backup:/backup" mongo \
  bash -c 'mongodump --out /backup --host mongo:27017'                                     

