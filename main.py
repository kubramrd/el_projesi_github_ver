import cv2 as cv 
import mediapipe as mp 
import numpy as np 
import os 
import datetime
import time
import csv
import pyotp
import hashlib
from utils import get_hand_features 

if not os.path.exists("kanitlar"): 
    os.makedirs("kanitlar")

bugun = datetime.datetime.now().strftime("%Y-%m-%d") 
kayit_yolu = os.path.join("kanitlar", bugun)
csv_yolu = os.path.join(kayit_yolu, "adli_loglar.csv")

if not os.path.exists(kayit_yolu):
    os.makedirs(kayit_yolu)

if not os.path.exists(csv_yolu):
    with open(csv_yolu, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Tarih", "Saat", "Durum", "P_Orani", "F_Orani", "S_Orani", "Dosya", "Hash_SHA256"])

SECRET_KEY = "JBSWY3DPEHPK3PXP"
totp = pyotp.totp.TOTP(SECRET_KEY)

mp_hands = mp.solutions.hands 
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.8) 

verification_start_time = None 
is_verified = False
mfa_authenticated = False
last_capture_time = 0 

def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def log_kaydet(durum, p, f, s, dosya_adi, dosya_yolu):
    su_an = datetime.datetime.now()
    tarih = su_an.strftime("%d-%m-%Y")
    saat = su_an.strftime("%H:%M:%S")
    f_hash = get_file_hash(dosya_yolu)
    with open(csv_yolu, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([tarih, saat, durum, p, f, s, dosya_adi, f_hash])

def main():
    global verification_start_time, is_verified, mfa_authenticated, last_capture_time 
    cap = cv.VideoCapture(0) 
    print(f"[SİSTEM] Adli Biyometrik Kayıt Aktif. Arşiv: {bugun}")

    while cap.isOpened(): 
        success, frame = cap.read() 
        if not success: break
        
        frame = cv.flip(frame, 1)
        rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB) 
        results = hands.process(rgb_frame) 
        
        if results.multi_hand_landmarks: 
            for hand_lms in results.multi_hand_landmarks:
                features = get_hand_features(hand_lms.landmark) 
                p, f, s = round(features[0], 2), round(features[1], 2), round(features[2], 2)
                check_yetkili = (0.44 <= p <= 0.52) and (0.85 <= f <= 0.95) and (0.68 <= s <= 0.78)
 
                if check_yetkili:
                    if verification_start_time is None: 
                        verification_start_time = time.time()
                    
                    elapsed = time.time() - verification_start_time 
                    remaining = max(0, 5 - int(elapsed)) 

                    if elapsed >= 5: 
                        if not is_verified:
                            is_verified = True
                            print("\n[BİYOMETRİK ONAY] El tanındı. Lütfen telefondaki MFA kodunu girin.")
                            otp_input = input("MFA KODU: ")
                            if totp.verify(otp_input):
                                mfa_authenticated = True
                                print("[ERİŞİM BAŞARILI] Kimlik doğrulandı.")
                            else:
                                mfa_authenticated = False
                                verification_start_time = None
                                is_verified = False
                                print("[HATA] Geçersiz MFA kodu!")

                        if mfa_authenticated:
                            status, color = "ERISIM YETKISI: KUBRA MERDE", (0, 255, 0)
                        else:
                            status, color = "MFA BEKLENIYOR...", (0, 255, 255)
                    else:
                        is_verified = False
                        status, color = f"DOGRULANIYOR... {remaining}s", (0, 255, 255) 
                else:
                    verification_start_time = None
                    is_verified = False
                    mfa_authenticated = False
                    status, color = "YETKISIZ / BILINMEYEN", (0, 0, 255) 

                cv.putText(frame, status, (20, 50), 2, 0.7, color, 2)
                cv.putText(frame, f"P:{p} F:{f} S:{s}", (20, 120), 0, 0.5, (255, 255, 255), 1)

                if verification_start_time and not is_verified:
                    bar_w = int((elapsed / 5) * 300)
                    cv.rectangle(frame, (20, 70), (20 + bar_w, 85), color, -1)

                mp_draw.draw_landmarks(
                    frame, 
                    hand_lms, 
                    mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=color, thickness=-1, circle_radius=5),
                    mp_draw.DrawingSpec(color=(255, 255, 255), thickness=2)
                )

                current_time = time.time()
                if (current_time - last_capture_time) > 15: 
                    zaman = datetime.datetime.now().strftime("%H%M%S")
                    if mfa_authenticated:
                        dosya_adi = f"ONAY_{zaman}.jpg"
                        yol = os.path.join(kayit_yolu, dosya_adi)
                        cv.imwrite(yol, frame)
                        log_kaydet("ONAY", p, f, s, dosya_adi, yol)
                        last_capture_time = current_time
                    elif not check_yetkili: 
                        dosya_adi = f"IHLAL_{zaman}.jpg"
                        yol = os.path.join(kayit_yolu, dosya_adi)
                        cv.imwrite(yol, frame)
                        log_kaydet("IHLAL", p, f, s, dosya_adi, yol)
                        last_capture_time = current_time
        else:
            verification_start_time = None
            is_verified = False
            mfa_authenticated = False

        cv.imshow("Firat Uni - Adli Biyometrik Sistem", frame) 
        if cv.waitKey(1) & 0xFF == ord('q'): break 

    cap.release() 
    cv.destroyAllWindows() 

if __name__ == "__main__": 
    main()