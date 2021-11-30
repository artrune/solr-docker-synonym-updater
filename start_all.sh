
docker build --tag synonym-updater:1 .
docker run -d -p 8983:8983 --name solr -v "$PWD\solrdata:/var/solr" -v "$PWD\conf:/mycore_config/conf" solr:8 solr-precreate mycore /mycore_config
docker run -v "$PWD\solrdata\data\mycore\conf:/mycore_config/conf" --name synonym-updater -p 8092:8092 -d synonym-updater:1
