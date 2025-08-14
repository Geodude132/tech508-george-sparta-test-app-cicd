#cloud-boothook
#!/bin/bash

export DB_HOST=mongodb://10.0.3.132:27017/posts

cd /repo/app

pm2 start app.js 