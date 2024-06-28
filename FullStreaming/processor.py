from tensorflow import io, image, expand_dims, clip_by_value, cast, uint8

from ModelUtil.models import Generator

# 모델 초기화
generator = Generator()
generator.load_weights("./ModelUtil/GeneratorVG4(1520).h5")


# 이미지를 TensorFlow 텐서로 변환하는 함수 정의
def decodeImage(image_bytes):
    # 바이너리 데이터를 텐서로 디코딩
    image_tensor = image.decode_image(
        image_bytes, channels=3
    )  # RGB 이미지로 디코딩, channels=3
    return image_tensor


# 이미지를 바이너리로 인코딩하는 함수 정의
def encodeImage(image_tensor):
    # 이미지를 PNG 형식으로 인코딩
    image_binary = io.encode_png(image_tensor)
    return image_binary


# 이미지 처리 함수
def processImage(image_data):
    image_tensor = decodeImage(image_data)

    # 이미지를 업스케일링하여 고해상도 이미지 생성
    sr_image = generator(expand_dims(image_tensor, 0), training=False)[0]

    # 이미지 클리핑 (0 이상 255 이하로)
    sr_image = clip_by_value(sr_image, 0, 255)

    # 이미지 데이터 타입 변환
    sr_image = cast(sr_image, uint8)

    # 이미지를 바이너리로 인코딩하여 클라이언트에게 전송
    processed_image_binary = encodeImage(sr_image)

    # 바이너리 데이터를 16진수 문자열로 변환
    processed_image_hex = (
        processed_image_binary.numpy().hex()
    )  # 여기는 변환 예시를 위해 원본 이미지 반환

    return processed_image_hex


# que에서 이미지를 가져와 병렬처리
def process(image_data):
    return processImage(image_data)
