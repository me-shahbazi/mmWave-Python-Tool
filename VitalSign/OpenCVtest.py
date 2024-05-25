import cv2
import numpy as np
import pickle

with open('tempData.pkl', 'rb') as f:
    dataList = pickle.load(f)

row = 64
col = 48
grayImg = np.zeros((row,col)).astype(np.uint8)

for frame in range(len(dataList)):
    frameMax = np.max(dataList[frame])
    scale = (frameMax // 255) + 1

    for row in range(len(grayImg)):
        for col in range(len(grayImg[0])):
            grayImg[row][col] = dataList[frame][row][col]//scale
    
    reSizedImg = cv2.resize(grayImg, (480,640), interpolation=cv2.INTER_NEAREST)
    # print("Frame Number: ", frame)
    cv2.imshow('GrayScaled Image', reSizedImg)
    cv2.waitKey(100)

cv2.destroyAllWindows()