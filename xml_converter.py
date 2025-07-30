import requests
import xml.etree.ElementTree as ET
import os
import re
from ftplib import FTP
import io

def clean_cdata(text):
    if text is None:
        return ""
    # CDATA ve HTML taglarını temizle
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'<.*?>', '', text, flags=re.DOTALL)
    return text.strip()

def get_text(elem, tag):
    found = elem.find(tag)
    if found is not None and found.text:
        return clean_cdata(found.text)
    return ""

def upload_to_ftp(xml_content, ftp_host, ftp_user, ftp_pass, ftp_path, filename):
    """XML içeriğini FTP ile hostinge yükler"""
    try:
        ftp = FTP(ftp_host)
        print(f"FTP sunucusuna bağlanıyor: {ftp_host}")
        ftp.login(ftp_user, ftp_pass)
        print("FTP girişi başarılı")
        
        # Mevcut dizini kontrol et
        current_dir = ftp.pwd()
        print(f"Mevcut dizin: {current_dir}")
        
        # Belirtilen dizine geç
        if ftp_path and ftp_path != "/":
            try:
                ftp.cwd(ftp_path)
                print(f"Dizin değiştirildi: {ftp_path}")
            except Exception as e:
                print(f"Dizin değiştirme hatası: {e}")
                # Dizini oluşturmayı dene
                try:
                    ftp.mkd(ftp_path)
                    ftp.cwd(ftp_path)
                    print(f"Dizin oluşturuldu ve değiştirildi: {ftp_path}")
                except:
                    print("Dizin oluşturulamadı, mevcut dizinde devam ediliyor")
        
        # Dosya listesini kontrol et
        files = ftp.nlst()
        print(f"Mevcut dosyalar: {files}")
        
        # XML içeriğini bytes olarak hazırla
        xml_bytes = xml_content.encode('utf-8')
        
        # FTP'ye yükle
        print(f"Dosya yükleniyor: {filename}")
        ftp.storbinary(f'STOR {filename}', io.BytesIO(xml_bytes))
        
        # Yükleme sonrası dosya listesini tekrar kontrol et
        files_after = ftp.nlst()
        print(f"Yükleme sonrası dosyalar: {files_after}")
        
        ftp.quit()
        print("FTP bağlantısı kapatıldı")
        return True
    except Exception as e:
        print(f"FTP yükleme hatası: {e}")
        return False

def convert_xml(source_url, ftp_host, ftp_user, ftp_pass, ftp_path, filename):
    # XML'i indir
    response = requests.get(source_url)
    response.encoding = 'utf-8'
    root = ET.fromstring(response.text)

    # Yeni XML kökü
    new_root = ET.Element("products")

    # Script taglerini ekle (varsa)
    for script in root.findall("script"):
        new_root.append(script)

    for product in root.findall("product"):
        new_product = ET.SubElement(new_root, "product")
        # Alanlar, örnek eşleştirme
        ET.SubElement(new_product, "id").text = get_text(product, "code")
        ET.SubElement(new_product, "productCode").text = get_text(product, "ws_code")
        ET.SubElement(new_product, "barcode").text = get_text(product, "barcode")
        ET.SubElement(new_product, "main_category").text = get_text(product, "cat1name")
        ET.SubElement(new_product, "top_category").text = get_text(product, "cat2name")
        ET.SubElement(new_product, "sub_category").text = get_text(product, "cat2name")
        ET.SubElement(new_product, "sub_category_").text = ""
        ET.SubElement(new_product, "categoryID").text = get_text(product, "cat1code")
        ET.SubElement(new_product, "category").text = get_text(product, "category_path")
        ET.SubElement(new_product, "active").text = "1"
        ET.SubElement(new_product, "brandID").text = "0"  # Kaynakta yoksa sabit ver
        ET.SubElement(new_product, "brand").text = get_text(product, "brand")
        ET.SubElement(new_product, "name").text = get_text(product, "name")
        ET.SubElement(new_product, "description").text = get_text(product, "detail")

        # Varyantlar
        variants_elem = ET.SubElement(new_product, "variants")
        subproducts = product.find("subproducts")
        if subproducts is not None:
            for sub in subproducts.findall("subproduct"):
                variant = ET.SubElement(variants_elem, "variant")
                ET.SubElement(variant, "name1").text = "Renk"
                ET.SubElement(variant, "value1").text = get_text(sub, "type1")
                ET.SubElement(variant, "name2").text = "Beden"
                ET.SubElement(variant, "value2").text = get_text(sub, "type2")
                ET.SubElement(variant, "quantity").text = get_text(sub, "stock")
                ET.SubElement(variant, "barcode").text = get_text(sub, "barcode")

        # Görseller
        images = product.find("images")
        if images is not None:
            img_tags = images.findall("img_item")
            for i, img in enumerate(img_tags):
                ET.SubElement(new_product, f"image{i+1}").text = clean_cdata(img.text)
        # Fiyatlar
        ET.SubElement(new_product, "listPrice").text = get_text(product, "price_list_vat_included")
        ET.SubElement(new_product, "price").text = get_text(product, "price_special_vat_included")
        vat_val = get_text(product, "vat")
        ET.SubElement(new_product, "tax").text = str(float(vat_val)/100 if vat_val else 0)
        ET.SubElement(new_product, "currency").text = get_text(product, "currency")
        ET.SubElement(new_product, "desi").text = get_text(product, "desi")
        ET.SubElement(new_product, "quantity").text = get_text(product, "stock")

    # XML'i string olarak oluştur
    xml_string = ET.tostring(new_root, encoding='unicode', xml_declaration=True)
    
    # FTP'ye yükle
    if upload_to_ftp(xml_string, ftp_host, ftp_user, ftp_pass, ftp_path, filename):
        print(f"XML başarıyla FTP'ye yüklendi: {filename}")
    else:
        print("FTP yükleme başarısız!")

if __name__ == "__main__":
    source_url = "https://www.jartiyertakim.com/xml/?R=15247&K=baff&AltUrun=1&TamLink=1&Dislink=1&Imgs=1&start=0&limit=99999&pass=Iia01UIU"# FTP bilgileri - Bu bilgileri kendi hosting bilgilerinizle değiştirin
    ftp_host = "ftp.eterella.com"  # FTP sunucu adresi
    ftp_user = "windamdx"       # FTP kullanıcı adı
    ftp_pass = "c_bJ!-PGMwG57#Hx"       # FTP şifresi
    ftp_path = "/public_html/yasinxml/"       # FTP dizin yolu
    filename = "jartiyerdeneme.xml"  # Dosya adı
    
    convert_xml(source_url, ftp_host, ftp_user, ftp_pass, ftp_path, filename) 