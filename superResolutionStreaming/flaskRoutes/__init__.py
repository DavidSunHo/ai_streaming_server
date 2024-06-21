import ray

import cv2 as cv
import numpy as np
from numpy import frombuffer
from os import environ

from RTMODEL.models import Generator
import tensorflow as tf

from collections import deque
from flask import Flask, request, jsonify


ray.init()

queue = deque([])

environ["KMP_DUPLICATE_LIB_OK"] = "True"

app = Flask(__name__)
app.debug = False

generator = Generator()
generator.load_weights("./RTMODEL/GeneratorVG4(1520).h5")


# 이미지를 TensorFlow 텐서로 변환하는 함수 정의
def decode_image(image_bytes):
    # 바이너리 데이터를 텐서로 디코딩
    image_tensor = tf.image.decode_image(
        image_bytes, channels=3
    )  # RGB 이미지로 디코딩, channels=3
    return image_tensor


# 이미지를 바이너리로 인코딩하는 함수 정의
def encode_image(image_tensor):
    # 이미지를 PNG 형식으로 인코딩
    image_binary = tf.io.encode_png(image_tensor)
    return image_binary


# 이미지 처리 함수
@ray.remote
@app.route("/upload", methods=["POST", "GET"])
def upload():
    try:
        # 클라이언트에서 이미지를 받음
        data = request.json
        image_bytes = bytes.fromhex(data["image"])

        # 이미지를 텐서로 변환
        image_tensor = decode_image(image_bytes)

        # # 이미지를 원하는 크기로 resize
        # target_size = [320, 180]  # 원하는 크기 설정
        # resized_image_tensor = tf.image.resize(
        #     image_tensor, target_size, method=tf.image.ResizeMethod.BICUBIC
        # )

        # 이미지를 업스케일링하여 고해상도 이미지 생성
        sr_image = generator(tf.expand_dims(image_tensor, 0), training=False)[0]

        # 이미지 클리핑 (0 이상 255 이하로)
        sr_image = tf.clip_by_value(sr_image, 0, 255)

        # 이미지 데이터 타입 변환
        sr_image = tf.cast(sr_image, tf.uint8)

        # 이미지를 바이너리로 인코딩하여 클라이언트에게 전송
        processed_image_binary = encode_image(sr_image)

        # 바이너리 데이터를 16진수 문자열로 변환
        processed_image_hex = processed_image_binary.numpy().hex()

        return jsonify({"processed_image": processed_image_hex})

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=False, threaded=True)
