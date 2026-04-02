import numpy as np

def get_hand_features(landmarks):
    lms = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
    
    # 1. El Ayası Oranı (P)
    palm_width = np.linalg.norm(lms[5] - lms[17])
    palm_length = np.linalg.norm(lms[0] - lms[5])
    p_ratio = round(palm_width / palm_length, 4)

    # 2. İşaret / Orta Parmak Oranı (F)
    index_len = np.linalg.norm(lms[5] - lms[8])
    middle_len = np.linalg.norm(lms[9] - lms[12])
    f_ratio = round(index_len / middle_len, 4)

    # 3. Serçe Parmak / El Ayası Oranı (S)
    pinky_len = np.linalg.norm(lms[17] - lms[20])
    s_ratio = round(pinky_len / palm_length, 4)

    return [p_ratio, f_ratio, s_ratio]