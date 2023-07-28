import numpy as np
import cv2
import threading
import time
from packages.ImageProcess import ImageProcess, Plot


class CamCapture:
    def __init__(self, cam1Path, cam2Path, cam3Path, cam4Path, size, videoMode, logger) -> None:
        self.size = size
        self.videoMode = videoMode
        self.logger = logger

        self.combineImg = np.zeros((size * 2, size * 2, 3), np.uint8)
        camImg = np.zeros((size, size, 3), np.uint8)
        self.camDict = {
            "1": {
                "enable": True if cam1Path is not None else False,
                "camPath": cam1Path,
                "capture": None,
                "camImg": camImg,
                "flag": True,
                "xyxy": [1, 2, 0, 1],
            },
            "2": {
                "enable": True if cam2Path is not None else False,
                "camPath": cam2Path,
                "camImg": camImg,
                "flag": True,
                "xyxy": [0, 1, 0, 1],
            },
            "3": {
                "enable": True if cam3Path is not None else False,
                "camPath": cam3Path,
                "camImg": camImg,
                "flag": True,
                "xyxy": [0, 1, 1, 2],
            },
            "4": {
                "enable": True if cam4Path is not None else False,
                "camPath": cam4Path,
                "camImg": camImg,
                "flag": True,
                "xyxy": [1, 2, 1, 2],
            },
        }

        for camId, camData in self.camDict.items():
            if camData["enable"]:
                camPath = camData["camPath"]
                camThread = threading.Thread(target=self.cam_read, args=(camPath, camId))
                camThread.start()

    def cam_read(self, camPath, camId):
        cap = cv2.VideoCapture(camPath)
        ret, frame = cap.read()
        if ret:
            frame = ImageProcess.get_fisheye(frame)
            frame = cv2.resize(frame, (2160, 2160))
            cv2.imwrite(f"./data/images/{camId}.jpg", frame)
        else:
            self.logger.error(f"Error to open cam{camId}!")

        isNoFrame = False
        noFrameCnt = 0
        while True:
            time.sleep(0.0001)

            ###  video mode 同步攝影機讀取速度
            if not self.camDict[camId]["flag"]:
                continue

            ret, frame = cap.read()
            if ret:
                ### 記錄恢復影像串流
                if isNoFrame:
                    self.logger.info(f"Cam{camId} connected!")
                    isNoFrame = False
                    noFrameCnt = 0
                ### XXX: yjchou 2023/06/21 sidadun 測試影片比例錯誤修正
                if False:
                    frame = frame[0:1536, 1024 - 768 : 1024 + 768]
                frame = ImageProcess.get_fisheye(frame)
                resizeImg = cv2.resize(frame, (self.size, self.size))
                self.camDict[camId]["camImg"] = resizeImg
                if self.videoMode:
                    self.camDict[camId]["flag"] = False
            else:
                ### 記錄影像串流異常
                if not isNoFrame:
                    self.logger.error(f"Cann't capture cam{camId}!")
                    isNoFrame = True
                noFrameCnt += 1

                ### 重啟攝影機
                if noFrameCnt > 100:
                    cap = cv2.VideoCapture(camPath)
                    self.logger.debug(f"Cam{camId} reload!")
                    noFrameCnt = 0
                else:
                    disconnectedImg = Plot.plot_disconnected_img((self.size, self.size), fontSize=10)
                    self.camDict[camId]["camImg"] = disconnectedImg

    def get_frame(self):
        for camId, camData in self.camDict.items():
            x1, x2, y1, y2 = camData["xyxy"]
            self.combineImg[self.size * y1 : self.size * y2, self.size * x1 : self.size * x2] = camData["camImg"]
            camData["flag"] = True
        return self.combineImg


if __name__ == "__main__":
    cam1Path = "rtsp://admin:Auo+84149738@192.168.226.201/profile1"
    cam2Path = "rtsp://admin:Auo+84149738@192.168.226.202/profile1"
    cam3Path = "rtsp://admin:Auo+84149738@192.168.226.203/profile1"
    cam4Path = "rtsp://admin:Auo+84149738@192.168.226.204/profile1"
    # cam1Path = r"data\videos\cam1_demo.mp4"
    # cam2Path = r"data\videos\cam2_demo.mp4"
    # cam3Path = r"data\videos\cam3_demo.mp4"
    # cam4Path = r"data\videos\cam4_demo.mp4"
    camCapture = CamCapture(cam1Path, cam2Path, cam3Path, cam4Path, videoMode=False)

    while True:
        framImg = camCapture.get_frame()
        cv2.imshow("frame", framImg)
        cv2.waitKey(1)
