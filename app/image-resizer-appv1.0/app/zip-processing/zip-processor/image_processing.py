import os
import tempfile
import zipfile
import random
import string
from PIL import Image

def random_prefix(length=6):
    return ''.join(random.choices(string.ascii_letters, k=length))

def safe_zip_filename(original_filename, prefix_length=6, max_length=255):
    name, ext = os.path.splitext(original_filename)
    prefix = random_prefix(prefix_length) + '_'
    reserved = len(prefix) + len('_reduced') + len(ext)
    max_name_length = max_length - reserved
    if len(name) > max_name_length:
        name = name[:max_name_length]
    return f"{prefix}{name}_reduced{ext}"

def add_reduced_suffix(filename):
    name, ext = os.path.splitext(filename)
    return f"{name}_reduced{ext}"

def extract_and_resize(zip_path, output_dir, percent, correlation_id, output_zip_name=None):
    extracted_dir = os.path.join(output_dir, correlation_id)
    os.makedirs(extracted_dir, exist_ok=True)
    resized_files = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            # Preserve folder structure
            rel_path = info.filename
            folder = os.path.dirname(rel_path)
            filename = os.path.basename(rel_path)
            if not filename:
                continue
            reduced_filename = add_reduced_suffix(filename)
            out_folder = os.path.join(extracted_dir, folder)
            os.makedirs(out_folder, exist_ok=True)
            out_path = os.path.join(out_folder, reduced_filename)
            with zf.open(info) as file:
                img = Image.open(file)
                new_size = (max(1, int(img.width * percent / 100)), max(1, int(img.height * percent / 100)))
                img_resized = img.resize(new_size, Image.LANCZOS)
                img_resized.save(out_path)
                resized_files.append((out_path, os.path.join(folder, reduced_filename)))
    # Use output_zip_name if provided, else fallback to old logic
    if output_zip_name is None:
        output_zip_name = f"{correlation_id}_reduced.zip"
    output_zip = os.path.join(output_dir, output_zip_name)
    with zipfile.ZipFile(output_zip, 'w') as outzip:
        for file_path, arcname in resized_files:
            outzip.write(file_path, arcname=arcname)
    return output_zip, extracted_dir
