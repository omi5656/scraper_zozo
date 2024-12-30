# ZOZOTOWN商品スクレイピングツール

ZOZOTOWNの商品情報を収集し、データ分析を行うPythonスクリプト。

## 機能

- カテゴリページからの商品情報収集
- 商品データのCSV/SQLite保存
- データの可視化と分析
- エラーハンドリングとリトライ機能

## 収集データ

- 商品名
- ブランド名
- 価格（通常・割引）
- 評価とレビュー数
- 商品画像URL
- 商品詳細ページURL

## 必要条件

### Python環境
- Python 3.8以上

### 必要ライブラリ
```bash
pip install -r requirements.txt
```

requirements.txt:
```
beautifulsoup4>=4.9.3
pandas>=1.2.0
selenium>=4.0.0
matplotlib>=3.3.0
seaborn>=0.11.0
```

### Chromeドライバー
1. Google Chromeをインストール
2. ChromeDriverをダウンロード（Chromeと同じバージョン）
3. ChromeDriverをPATHに追加

## 使用方法

1. リポジトリのクローン:
```bash
git clone [リポジトリURL]
cd zozotown-scraper
```

2. 設定の変更（オプション）:
```python
scraper = ZozoScraper(
    max_items=200,  # 収集する最大商品数
    retry_count=3,  # リトライ回数
    delay_range=(1, 3)  # リクエスト間隔（秒）
)
```

3. スクリプト実行:
```bash
python main.py
```

## 出力ファイル

- `products.csv`: 収集データ（CSV形式）
- `zozo_products.db`: SQLiteデータベース
- `analysis/`: データ分析結果
  - `price_distribution.png`: 価格分布
  - `brand_distribution.png`: ブランド分布
  - `price_rating_correlation.png`: 価格と評価の相関
  - `statistics.json`: 基本統計情報

## エラーハンドリング

- タイムアウト時の自動リトライ
- ログファイル（scraping.log）への記録
- bot対策機能搭載

## 制限事項

- ZOZOTOWNの利用規約に従う
- 過度なリクエストを避ける
- 1リクエストあたり1-3秒の待機時間

## トラブルシューティング

1. ChromeDriverエラー:
   - Chromeとドライバーのバージョン一致を確認
   - PATH設定の確認

2. スクレイピングエラー:
   - ネットワーク接続確認
   - ログファイル確認
   - リトライ回数増加

## ライセンス

MIT License
