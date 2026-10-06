import zipfile
import os

zip_path = r"c:\Users\i7\Downloads\empire_ali\Empire\Empire_fayllar.zip"
extract_path = r"c:\Users\i7\Downloads\empire_ali\Empire\utils\others.py"
target_file_in_zip = None

try:
    with zipfile.ZipFile(zip_path, 'r') as z:
        # Fayl nomlarini tekshirish (papkalar bilan yozilgan bo'lishi mumkin)
        for name in z.namelist():
            if name.endswith("others.py"):
                target_file_in_zip = name
                break
        
        if target_file_in_zip:
            with z.open(target_file_in_zip) as source, open(extract_path, 'wb') as target:
                target.write(source.read())
            print(f"Muvaffaqiyatli tiklandi: {target_file_in_zip}")
        else:
            print("others.py arxiv ichidan topilmadi.")
except Exception as e:
    print(f"Xatolik: {e}")
