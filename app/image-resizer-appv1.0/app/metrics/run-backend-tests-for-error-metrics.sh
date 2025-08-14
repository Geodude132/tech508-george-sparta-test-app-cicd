#!/bin/bash

# Purpose: 1. Generate the full range of errors possible on the backend
#          2. Want to see the errors affect the error metrics on Grafana

# Why needed: Running the unit tests with pytest will not add to the metrics

# How to use:
# 1. Get the backend running
# 2. To see the how the error metrics are affected, start Prometheus and Grafana
# 3. Copy and run this script file from where the images used below are located

echo '********************************************************************************'
echo 'Run test similar to unit test "test_upload_no_file"...'
echo '  Should return "No file uploaded"'
curl -X POST http://localhost:5000/upload -F "percent=50"
echo Done!
echo '********************************************************************************'
echo

echo '********************************************************************************'
echo 'Run test similar to unit test "test_upload_invalid_filetype"...'
echo '  Should return "Only image files accepted. Upload a gif, jpg, jpeg or png"'
curl -F "image=@invoice.pdf" -F "percent=50" http://localhost:5000/upload
echo Done!
echo '********************************************************************************'
echo

echo '********************************************************************************'
echo 'Run test similar to unit test "test_upload_percent_out_of_range"...'
echo '  Should return "Invalid percentage"'
curl -F "image=@paradise01.jpg" -F "percent=0" http://localhost:5000/upload
echo Done!
echo '********************************************************************************'
echo

echo '********************************************************************************'
echo 'Run test similar to unit test "test_upload_invalid_percent"...'
echo '  Should return "Invalid percentage"'
curl -F "image=@paradise01.jpg" -F "percent=abc" http://localhost:5000/upload
echo Done!
echo '********************************************************************************'
echo

echo '********************************************************************************'
echo 'Run test similar to unit test "test_upload_invalid_image_content"'
echo '  Should return "Internal server error"'
curl -F "image=@not-a-real-image.jpg" -F "percent=50" http://localhost:5000/upload
echo Done!
echo '********************************************************************************'
echo
echo All tests done!