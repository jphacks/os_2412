import json
import os
from datetime import datetime

class MetadataManager:
    def __init__(self, metadata_file):
        self.metadata_file = metadata_file
        self.ensure_metadata_file()

    def ensure_metadata_file(self):
        """メタデータファイルが存在しない場合は作成"""
        if not os.path.exists(self.metadata_file):
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            self.save_metadata({})

    def load_metadata(self):
        """メタデータの読み込み"""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def save_metadata(self, metadata):
        """メタデータの保存"""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def save_image_data(self, image_data):
        """画像データの保存"""
        metadata = self.load_metadata()
        image_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        metadata[image_id] = image_data
        self.save_metadata(metadata)
        return image_id

    def get_image_data(self, image_id):
        """画像データの取得"""
        metadata = self.load_metadata()
        return metadata.get(image_id)

    def get_all_images(self):
        """全画像データの取得"""
        return self.load_metadata()