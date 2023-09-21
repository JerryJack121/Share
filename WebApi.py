import requests
import threading
import time
import datetime
import queue
from dataclasses import dataclass
from const.GlobalObject import Global


@dataclass
class Url:
    initUrl: str
    heatmapUrl: str
    areaVisitorUrl: str
    addAvgTimeUrl: str


class WebApi:
    def __init__(self, initUrl, heatmapUrl, areaVisitorUrl, addAvgTimeUrl, postInerval, areaNameList, logger):
        """前端串接API (熱力圖/各區人數/各區平均停留時間)

        Args:
            initUrl (str): 請求目前 DB 的最後一筆資料的 API
            heatmapUrl (str): 熱力圖 API
            areaVisitorUrl (str): 各區人數 API
            addAvgTimeUrl (str): 各區平均停留時間 API
            postInerval (str): API 刷新頻率
            areaNameList (list): 展區編號
            logger (Logger): Sub logger
        """
        ### 參數初始化
        self.urlCls = Url(initUrl, heatmapUrl, areaVisitorUrl, addAvgTimeUrl)
        self.postInerval = postInerval
        self.logger = logger
        self.IdPostQueue = queue.Queue()  # 待上傳停留時間的 ID 序列

        ### 變數初始化
        self.areaNameList = areaNameList  # 展區編號
        self.areaVisitorData, self.heatmapCountData = None, None  # 各區人數資料, 熱力圖與人數資料
        self.lastTimePost = 0  # 紀錄前一次上拋資料的時間

    def start_post_thread(self):
        """啟動 API 執行序"""
        self.postThread = threading.Thread(target=self.__post_thread)
        self.postThread.start()

    def get_init_data(self):
        """請求目前 DB 的最後一筆資料

        Returns:
            dict: 當天總人次, 各展區下一個可使用的 ID
        """
        dateToday = datetime.datetime.today().strftime("%Y%m%d")
        try:
            initData = requests.get(self.urlCls.initUrl).json()
            cntDay, noidList = int(initData[0]), initData[1]
            initDataDict, idList = dict(), list()

            ### XXX: yjchou 2023/06/08 展區 1 不一定是入口
            ### 從入口展區ID更新日期確定當日人次最後更新日
            fence1Noid = noidList[0]  # noid 編碼規則: [日期]_[人記數]_[展區編號]
            cntDayupdateDate = fence1Noid.split("_")[0]  # 入口展區更新日期

            ### 當天DB沒有人次資料
            if cntDayupdateDate != dateToday:
                initDataDict["cntDay"] = 0
            else:
                initDataDict["cntDay"] = cntDay

            for noid in noidList:
                ### DB 沒有該展區資料
                if noid == "":
                    id = 0
                else:
                    updateDate = noid.split("_")[0]
                    ### 該展區當天有資料
                    if updateDate == dateToday:
                        id = noid.split("_")[1]  # noid 編碼規則: [日期]_[人記數]_[展區編號]
                        id = int(id) + 1  # 下一個 id 從 id+1 開始
                    else:
                        id = 0
                idList.append(id)
            initDataDict["idList"] = idList

        except Exception as e:
            self.logger.warning("無法取得DB的最後一筆資料: " + str(e))
            ### API 請求失敗重置資料
            initDataDict = dict({"cntDay": 0, "idList": list((0 for i in range(1, 9)))})

        return initDataDict

    def update_area_visitor(self, fenceCntDict):
        """更新各區人數

        Args:
            fenceCntDict (dict): 各區人數
        """
        cntList = list()
        for fenceId, fenceCnt in fenceCntDict.items():
            cntList.append(fenceCnt)
        self.areaVisitorData = {"area": str(self.areaNameList), "count": str(cntList)}

    def update_heatmap_and_count(self, peopleCount, heatMapData, accCount):
        """更新熱力圖, 館內人數, 當天總人次

        Args:
            peopleCount (int): 館內人數
            heatMapData (list): 熱力圖 (x, y, level)
            accCount (int): 當天總人次
        """
        self.heatmapCountData = {"all_count": peopleCount, "acc_count": accCount, "data": str(heatMapData)}

    def update_IdPostQueue(self, exitIdDict):
        """當有ID離開, 將進出時間資訊放入Queue, 等待上傳至DB

        Args:
            exitIdDict (dict): 離開的ID進出時間資訊
        """
        ### 將exitIdDict放入序列等待上傳
        for fenceNum in exitIdDict.keys():
            fenceExitIdDict = exitIdDict[fenceNum]
            ### 任何一個圍籬區有資料就放入Queue
            if len(fenceExitIdDict) != 0:
                self.IdPostQueue.put(exitIdDict)
                break

        ### Develop: yjchou 2023/06/08 查看資料塞車狀況
        if False:
            print("IdPostQueue size: {}".format(self.IdPostQueue.qsize()))

    def __post_areaVisitorUrl(self):
        """上傳各區人數"""
        try:
            r = requests.post(self.urlCls.areaVisitorUrl, data=self.areaVisitorData)
        except Exception as e:
            self.logger.error(f"Post areaVisitorUrl error: {e}")

    def __post_heatmapUrl(self):
        """上傳熱力圖"""
        try:
            r = requests.post(self.urlCls.heatmapUrl, data=self.heatmapCountData)
        except Exception as e:
            self.logger.error(f"Post heatmapUrl error: {e}")

    def __post_addAvgTimeUrl(self, exitIdDict):
        """上傳離開的ID進出時間資訊

        Args:
            exitIdDict (dict): 離開的ID進出時間資訊
        """
        timeNow = datetime.datetime.today()
        dateFormat = timeNow.strftime("%Y%m%d")

        ### 上傳停留時間大於閾值的資料
        for fenceNum in exitIdDict.keys():
            for exitId, info in exitIdDict[fenceNum].items():
                ### noid 編碼規則: [日期]_[ID]_[展區編號]
                noid = dateFormat + "_" + str(exitId) + "_" + str(fenceNum)
                data = dict(
                    {
                        "noid": noid,
                        "area_num": fenceNum,
                        "time_in": info["startTime"],
                        "time_out": info["endTime"],
                        "duration": info["stayTime"],
                    }
                )
                try:
                    r = requests.post(self.urlCls.addAvgTimeUrl, data=data)
                except Exception as e:
                    self.logger.error(f"Post exitIdDict error: {e}")
                    break

    def __post_thread(self):
        runDate = datetime.date.today()  # 記錄系統啟動日期

        while True:
            today = datetime.date.today()
            ### 遇到跨日先判斷系統是否已重置
            if today != runDate:
                if Global.dailyResetFlag:
                    runDate = today
                    Global.dailyResetFlag = False
                ### 如果還沒就先不拋資料
                else:
                    continue

            ### 接近跨日都不拋資料
            t1 = datetime.datetime.strptime(str(today) + "12:00", "%Y-%m-%d%H:%M")
            timeNow = datetime.datetime.now()
            if timeNow > t1:
                t2 = datetime.datetime.strptime(str(today + datetime.timedelta(days=1)) + "00:00", "%Y-%m-%d%H:%M")
            else:
                t2 = datetime.datetime.strptime(str(today) + "00:00", "%Y-%m-%d%H:%M")

            duration = t2 - timeNow
            if duration > datetime.timedelta(minutes=-3) and duration < datetime.timedelta(minutes=3):
                continue

            timeNow = time.time()
            timeInterval = timeNow - self.lastTimePost

            ### 還沒有值或時間間隔不足就等待
            if self.areaVisitorData is None or self.heatmapCountData is None or timeInterval < self.postInerval:
                time.sleep(self.postInerval)
            else:
                ### 上傳熱力圖/各區人數
                self.lastTimePost = timeNow
                self.__post_areaVisitorUrl()
                self.__post_heatmapUrl()

                ### 若IdPostQueue不為空, 上傳各區離開ID的停留時間資訊
                if not self.IdPostQueue.empty():
                    exitIdDict = self.IdPostQueue.get()
                    self.__post_addAvgTimeUrl(exitIdDict)
