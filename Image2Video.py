import cv2
import datetime
import time
import os
import threading


class Image2Video:
    def __init__(self, outputPath, fps=None, frameBefore=0, frameAfter=0):
        self.outputPath = outputPath
        self.fps = fps
        self.frameBefore, self.frameAfter = frameBefore, frameAfter
        self.fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        self.frameTmpList = list()
        self.recordList = list()
        self.recording, self.redayStopRecord, self.threadRunning = False, False, False
        self.updateTimeDict = dict()
        self.frameAfterCnt = 0

        self.threadDict = dict()

        os.makedirs(outputPath, exist_ok=True)

    def update_frame(self, frame):
        ### 暫存影像
        self.frameTmpList.append(frame)
        ### 控制暫存影像在近 frameBefore 幀
        if len(self.frameTmpList) > self.frameBefore:
            self.frameTmpList = self.frameTmpList[-self.frameBefore :]

        if self.recording:
            ### 錄影中將新的 frame 加入 recordList
            if not self.redayStopRecord:
                self.recordList.append(frame)
            ### 準備結束錄影, 將 frameAfter 個 frame 加入 recordList 後停止錄影
            else:
                if self.frameAfterCnt < self.frameAfter:
                    self.recordList.append(frame)
                    self.frameAfterCnt += 1
                else:
                    self.recording = False
                    self.redayStopRecord = False

        ### 若沒有設定 fps, 以 frame 的更新頻率計算
        if self.fps is None:
            if len(self.updateTimeDict.keys()) < 10:
                frameId = len(self.updateTimeDict.keys())
                self.updateTimeDict[frameId] = time.time()
            else:
                self.__cal_fps()

    def start_record(self):
        self.frameAfterCnt = 0
        ### 判斷還在錄影中, 接續錄影
        if self.recording:
            self.redayStopRecord = False
        ### 新增寫入影片
        else:
            ### 等待上一段影片寫入完成
            while self.threadRunning:
                time.sleep(0.1)
                print("等待上一段影片寫入完成")
            ### 將最新的幾 frame 加入儲存列表
            self.recordList = self.frameTmpList[-self.frameBefore :]
            self.recording = True
            videoWriteThread = threading.Thread(target=self.video_write)
            videoWriteThread.start()

    def stop_record(self):
        self.redayStopRecord = True

    def __cal_fps(self):
        calLen = len(self.updateTimeDict.keys()) - 1
        t1 = self.updateTimeDict[0]
        t2 = self.updateTimeDict[calLen]
        timeInterval = t2 - t1
        self.fps = int(calLen / timeInterval)
        if self.fps == 0:
            self.fps = 1

    def video_write(self):
        self.threadRunning = True
        # print("開始錄影\n")
        now = datetime.datetime.now()
        fileName = datetime.datetime.strftime(now, "%Y%m%d_%H%M%S") + ".mp4"

        ### 等待 fps 計算完成
        while self.fps is None or len(self.frameTmpList) == 0:
            time.sleep(1)

        ### 定義 videoWriter
        (h, w, _) = self.frameTmpList[0].shape
        self.videoWriter = cv2.VideoWriter(os.path.join(self.outputPath, fileName), self.fourcc, self.fps, (w, h))

        waitingFinish = False
        while True:
            if len(self.recordList) != 0:
                self.videoWriter.write(self.recordList[0])
                self.recordList = self.recordList[1:]

            else:
                time.sleep(0.1)

            ### 寫完全部的 frame 才結束錄影
            if not self.recording:
                waitingFinish = True
            if len(self.recordList) == 0 and waitingFinish:
                break
        self.videoWriter.release()
        # print("錄影完成\n")
        self.threadRunning = False
