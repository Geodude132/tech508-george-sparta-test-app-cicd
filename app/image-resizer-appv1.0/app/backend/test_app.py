import os
import io
import time
import pytest
from PIL import Image
from app import app, UPLOAD_FOLDER

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def cleanup_uploads():
    # Clean up uploads before and after each test
    yield
    for f in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, f)
        for _ in range(3):  # Retry up to 3 times
            try:
                os.remove(file_path)
                break
            except PermissionError:
                time.sleep(0.1)
        else:
            # If still failing after retries, print a warning (don't crash the test suite)
            print(f"Warning: Could not delete {file_path} (still in use)")

def create_test_image(format='JPEG'):
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes

def test_upload_success(client):
    img_bytes = create_test_image()
    data = {
        'image': (img_bytes, 'test.jpg'),
        'percent': '50'
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'filename' in json_data
    assert json_data['message'] == 'Image resized'

def test_upload_no_file(client):
    data = {'percent': '50'}
    response = client.post('/upload', data=data)
    assert response.status_code == 400
    assert response.get_json()['error'] == 'No file uploaded'

def test_upload_invalid_filetype(client):
    data = {
        'image': (io.BytesIO(b'notanimage'), 'test.txt'),
        'percent': '50'
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'Only image files accepted' in response.get_json()['error']

def test_upload_invalid_percent(client):
    img_bytes = create_test_image()
    data = {
        'image': (img_bytes, 'test.jpg'),
        'percent': 'abc'
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.get_json()['error'] == 'Invalid percentage'

def test_upload_percent_out_of_range(client):
    img_bytes = create_test_image()
    data = {
        'image': (img_bytes, 'test.jpg'),
        'percent': '0'
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.get_json()['error'] == 'Invalid percentage'

def test_download(client):
    # First upload an image
    img_bytes = create_test_image()
    data = {
        'image': (img_bytes, 'test.jpg'),
        'percent': '50'
    }
    upload_resp = client.post('/upload', data=data, content_type='multipart/form-data')
    filename = upload_resp.get_json()['filename']
    # Now download
    download_resp = client.get(f'/download/{filename}')
    assert download_resp.status_code == 200
    assert download_resp.data  # Should return file content

def test_metrics(client):
    response = client.get('/metrics')
    assert response.status_code == 200
    assert b'request_count' in response.data

def test_upload_invalid_image_content(client):
    # Simulate a PDF file renamed as .jpg
    fake_pdf_content = b'%PDF-1.4 fake pdf content'
    data = {
        'image': (io.BytesIO(fake_pdf_content), 'fakeimage.jpg'),
        'percent': '50'
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 500
    assert 'Internal server error' in response.get_json()['error']

def test_safe_upload_filename_and_reduced():
    from app import safe_upload_filename, safe_reduced_filename, random_prefix
    # Test normal case
    orig = 'photo.jpg'
    upload = safe_upload_filename(orig)
    assert upload.endswith('.jpg')
    assert upload.count('_') == 1
    assert len(upload.split('_')[0]) == 6
    # Test long filename
    base = 'a' * 300
    orig = base + '.png'
    upload = safe_upload_filename(orig)
    assert len(upload) <= 255
    # Test reduced filename
    reduced = safe_reduced_filename(upload)
    assert reduced.endswith('.png')
    assert reduced.count('_reduced') == 1
    assert len(reduced) <= 255
    # Test already reduced
    already = upload.replace('.png', '_reduced.png')
    reduced2 = safe_reduced_filename(already)
    assert reduced2 == already
    # Test edge case: exactly at limit
    base = 'b' * (255 - len('_reduced.png') - 7)  # 6 prefix + _ + ext + _reduced
    orig = base + '.png'
    upload = safe_upload_filename(orig)
    reduced = safe_reduced_filename(upload)
    assert len(reduced) <= 255
