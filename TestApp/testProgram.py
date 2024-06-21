import cv2
import threading
import requests
import base64
import sys
import numpy as np
from PyQt5 import QtWidgets, QtGui


class CameraApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.running = False

        self.label_original = QtWidgets.QLabel()
        self.label_processed = QtWidgets.QLabel()

        self.btn_start = QtWidgets.QPushButton("Camera On")
        self.btn_stop = QtWidgets.QPushButton("Camera Off")

        # 서버 URL
        self.server_url = "http://172.30.1.79:5000/upload"

        hbox = QtWidgets.QHBoxLayout()  # 수평 상자 레이아웃 생성
        hbox.addWidget(self.label_original)
        hbox.addWidget(self.label_processed)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.btn_start)
        vbox.addWidget(self.btn_stop)

        self.setLayout(vbox)

        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)

        QtWidgets.QApplication.instance().aboutToQuit.connect(self.onExit)

    def run(self):
        cap = cv2.VideoCapture(0)

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 비율을 유지하면서 너비를 95로 조정
        target_width = 180
        target_height = int((target_width / width) * height)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)

        while self.running:
            ret, img = cap.read()

            # # 이미지 크기 출력
            # print("Resized Image Size:", img.shape)

            if ret:
                img_original = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img_original = cv2.flip(img_original, 1)

                # 이미지 서버 전송
                image_encoded = self.encode_image(img_original)
                response = requests.post(self.server_url, json={"image": image_encoded})

                # 서버 응답 확인
                responseImg = response.json()
                processed_image_hex = responseImg.get("processed_image", "")

                # 화면에 개선된 프레임 표시
                frameSR = self.decode_image(processed_image_hex)

                original = cv2.resize(img_original, (1200, 900))
                frameSR = cv2.resize(frameSR, (1200, 900))

                cv2.putText(
                    frameSR,
                    "Processed Frame",
                    (10, 30),  # 텍스트 시작 위치 (x, y)
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,  # 폰트 크기
                    (255, 255, 255),  # 텍스트 색상 (BGR 형식)
                    2,  # 두께
                    cv2.LINE_AA,  # 안티앨리어싱
                )
                h_proc, w_proc, c_proc = frameSR.shape
                qImg_proc = QtGui.QImage(
                    frameSR.data,
                    w_proc,
                    h_proc,
                    w_proc * c_proc,
                    QtGui.QImage.Format_RGB888,
                )
                pixmap_proc = QtGui.QPixmap.fromImage(qImg_proc)
                self.label_processed.setPixmap(pixmap_proc)

                # 화면에 기존 프레임 표시
                cv2.putText(
                    original,
                    "Original Frame",
                    (10, 30),  # 텍스트 시작 위치 (x, y)
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,  # 폰트 크기
                    (255, 255, 255),  # 텍스트 색상 (BGR 형식)
                    2,  # 두께
                    cv2.LINE_AA,  # 안티앨리어싱
                )
                h_orig, w_orig, c_orig = original.shape
                qImg_orig = QtGui.QImage(
                    original.data,
                    w_orig,
                    h_orig,
                    w_orig * c_orig,
                    QtGui.QImage.Format_RGB888,
                )
                pixmap_orig = QtGui.QPixmap.fromImage(qImg_orig)
                self.label_original.setPixmap(pixmap_orig)

            else:
                QtWidgets.QMessageBox.about(self, "Error", "Cannot read frame.")
                print("Cannot read frame.")
                break

        cap.release()
        print("Thread end.")

    # 이미지를 base64로 인코딩하는 함수
    def encode_image(self, image):
        _, img_encoded = cv2.imencode(".png", image)
        encoded_string = img_encoded.tobytes().hex()
        return encoded_string

    # 이미지를 디코딩하여 numpy 배열로 변환하는 함수
    def decode_image(self, processed_image_hex):
        processed_image_binary = bytes.fromhex(processed_image_hex)
        processed_image_np = cv2.imdecode(
            np.frombuffer(processed_image_binary, dtype=np.uint8), cv2.IMREAD_COLOR
        )
        return processed_image_np

    def stop(self):
        self.running = False
        print("Stopped...")

    def start(self):
        self.running = True
        th = threading.Thread(target=self.run)
        th.start()
        print("Started...")

    def onExit(self):
        print("Exit")
        self.stop()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = CameraApp()
    window.show()
    sys.exit(app.exec_())
