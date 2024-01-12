import cv2

# 設定 rtsp 影像串流 URL
rtsp_url = "your_rtsp_url_here"

# 建立 OpenCV 視窗
cv2.namedWindow("RTSP Stream")

# 建立 VideoCapture 物件
cap = cv2.VideoCapture(rtsp_url)

# 設定影像寬度
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)

# 設定影像高度
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)


# 定義鍵盤事件處理函式
def on_key_press(key):
    if key == ord("s"):
        # 按下 s 鍵時，拍照並儲存為 image.jpg
        ret, frame = cap.read()
        cv2.imwrite("image.jpg", frame)
        print("Saved image.jpg")


# 顯示影像串流並等待鍵盤事件
while True:
    ret, frame = cap.read()
    cv2.imshow("RTSP Stream", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        # 按下 q 鍵時，結束程式
        break
    on_key_press(key)

# 釋放資源並關閉視窗
cap.release()
cv2.destroyAllWindows()
