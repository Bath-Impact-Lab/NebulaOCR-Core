# NebulaOCR-Core

NebulaOCR-Core is an optical character recognition (OCR) system designed to extract text from images with high accuracy. This project leverages modern machine learning techniques to provide reliable and efficient text recognition.

## Installation

You will need to install poppler ( https://poppler.freedesktop.org/ )

To install the python dependencies, use the following command:
```sh
pip install -r requirements.txt
```

## Development

To run the OCR locally, use the following command:
```sh
uvicorn main:app --host localhost --port 8080
```

## Deploy
To deploy to something like render using the Dockerfile:
```sh
docker build -t nebulaocr-core .
docker run -it --rm nebulaocr-core
```

or for you own server
```sh
sudo docker-compose up -d --build
```

## Contributing

We welcome contributions to improve NebulaOCR-Core! Please follow the guidelines below:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-xyz`).
3. Commit your changes (`git commit -am 'Add some feature'`).
4. Push to the branch (`git push origin feature-xyz`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.