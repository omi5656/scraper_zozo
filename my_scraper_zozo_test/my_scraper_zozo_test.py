# ############################################################################
# ZOZOTOWN商品スクレイピングツール
# 概要: ZOZOTOWNの商品情報を収集し、データ分析を行うスクリプト
# 主な機能:
# - 商品カテゴリページからの情報収集
# - 商品データのCSVおよびSQLiteへの保存
# - 収集データの可視化と分析
# - エラーハンドリングとリトライ機能
# ############################################################################

# 必要なライブラリのインポート
# - requests: HTTPリクエスト用（現在は主にSeleniumを使用）
# - BeautifulSoup: HTML解析用
# - pandas: データ処理用
# - sqlite3: データベース操作用
# - selenium: ブラウザ自動操作用
# - matplotlib/seaborn: データ可視化用
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from typing import List, Dict, Optional
import json
import os

# ロギング設定
# - レベル: INFO（情報レベルのログを記録）
# - フォーマット: タイムスタンプ - ログレベル - メッセージ
# - 出力先: ファイル（scraping.log）とコンソール
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraping.log'),
        logging.StreamHandler()
    ]
)


class ZozoScraper:
    """
    ZOZOTOWNスクレイピングの中核クラス
    商品情報の収集、保存、分析を行う機能を提供
    """

    def __init__(self, max_items: int = 200, retry_count: int = 3, delay_range: tuple = (1, 3)):
        """
        スクレイパーの初期化

        Parameters:
            max_items (int): 収集する最大商品数。デフォルトは200件
            retry_count (int): スクレイピング失敗時の再試行回数。デフォルトは3回
            delay_range (tuple): リクエスト間の待機時間範囲（秒）。デフォルトは1-3秒
        """
        self.max_items = max_items
        self.retry_count = retry_count
        self.delay_range = delay_range
        self.setup_selenium()

    def setup_selenium(self):
        """
        Seleniumドライバーの設定
        Chromeブラウザの起動オプションとbot対策の設定を行う
        """
        chrome_options = Options()
        # セキュリティとパフォーマンスの基本設定
        chrome_options.add_argument('--no-sandbox')  # サンドボックス制限を解除
        chrome_options.add_argument('--disable-dev-shm-usage')  # 共有メモリ使用の制限を解除

        # ウィンドウの位置とサイズの設定
        chrome_options.add_argument('--window-position=-1000,0')  # 左モニターに表示（座標は環境により調整）
        chrome_options.add_argument('--window-size=1000,800')  # ウィンドウサイズを1000x800に設定

        # bot対策：実際のブラウザと同じユーザーエージェントを設定
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # bot対策：自動化の検出を回避するための設定
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # 自動化フラグを無効化
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])  # 自動化表示を除外
        chrome_options.add_experimental_option('useAutomationExtension', False)  # 自動化拡張を無効化

        # WebDriverの初期化
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()  # ウィンドウを最大化

        # bot対策：JavaScriptでwebdriver判定を回避
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def get_page_with_retry(self, url: str) -> Optional[BeautifulSoup]:
        """
        ページ取得処理（リトライ機能付き）

        Args:
            url: スクレイピング対象のURL
        Returns:
            BeautifulSoup: パース済みのHTMLデータ（失敗時はNone）
        """
        for attempt in range(self.retry_count):
            try:
                # ページ読み込みの開始をログに記録
                logging.info(f"ページ {url} の読み込みを開始")
                print(f"ページを読み込み中: {url}")

                # ページの取得
                self.driver.get(url)

                # サイトの初期読み込みを待機
                time.sleep(1)  # 5秒間の固定待機

                # bot対策：人間らしい振る舞いを模倣
                # ランダムな高さまでスクロール
                scroll_height = random.randint(300, 700)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_height})")

                # ランダムな時間待機（3-7秒）
                wait_time = random.uniform(1, 3)
                time.sleep(wait_time)

                # ページのHTMLを取得してBeautifulSoupで解析
                return BeautifulSoup(self.driver.page_source, 'html.parser')

            except Exception as e:
                # エラー発生時の処理
                logging.error(f"取得試行 {attempt + 1} 失敗: {str(e)}")
                print(f"エラーが発生しました（試行 {attempt + 1}/{self.retry_count}）")

                # 最大リトライ回数に達した場合
                if attempt == self.retry_count - 1:
                    logging.error(f"{url} の取得に {self.retry_count} 回失敗しました")
                    print("最大試行回数を超えました。次のページに進みます。")
                    return None

                # 次のリトライまでランダムに待機（5-10秒）
                retry_wait = random.uniform(5, 10)
                print(f"リトライまで {retry_wait:.1f}秒待機します...")
                time.sleep(retry_wait)

    def parse_product(self, product_element) -> Dict:
        """
        カタログページから商品の基本情報を取得

        Args:
            product_element: 商品要素
        Returns:
            Dict: 商品の基本情報
        """
        try:
            # ブランド名の取得（クラス名から）
            brand_element = product_element.select_one('.css-1hsxkcj')
            brand = brand_element.text.strip() if brand_element else "ブランド情報なし"

            # 価格情報は詳細ページで取得するため、ここでは初期値をNoneに設定
            current_price = None
            original_price = None

            # 商品詳細ページURLの取得と修正
            url_element = product_element.select_one('a[href*="/shop/"]')
            if not url_element:
                raise ValueError("商品URLが見つかりません")

            original_url = url_element['href']

            # URLからショップ名、商品ID、DIDを抽出
            import re
            shop_match = re.search(r'/shop/([^/]+)/', original_url)
            gid_match = re.search(r'gid=(\d+)', original_url)
            did_match = re.search(r'did=(\d+)', original_url)

            if shop_match and gid_match and did_match:
                shop_name = shop_match.group(1)
                gid = gid_match.group(1)
                did = did_match.group(1)

                # 新しい形式でURLを構築
                product_url = f'https://zozo.jp/shop/{shop_name}/goods-sale/{gid}/?did={did}'
            else:
                product_url = 'https://zozo.jp' + original_url

            # 基本情報を辞書として返す
            return {
                'brand': brand,
                'original_price': original_price,
                'current_price': current_price,
                'product_url': product_url,
                'needs_details': True  # 詳細情報の取得が必要なフラグ
            }

        except Exception as e:
            logging.error(f"商品データの解析エラー: {str(e)}")
            return None

    def parse_product_detail(self, product_url: str) -> Dict:
        """
        商品詳細ページから追加情報を取得（非同期処理）

        Args:
            product_url: 商品詳細ページのURL
        Returns:
            Dict: 商品の詳細情報
        """
        try:
            # 詳細ページへのアクセス
            self.driver.get(product_url)
            time.sleep(1)  # ページ読み込み待機

            # 詳細ページのHTMLを解析
            detail_soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # 商品名の取得
            name_element = detail_soup.select_one('.p-goods-information__heading')
            name = name_element.text.strip() if name_element else "商品名なし"

            # レビュー情報の取得
            rating = None
            review_count = 0

            rating_element = detail_soup.select_one('.c-rating')
            if rating_element:
                try:
                    # aria-label属性から評価値を抽出
                    aria_label = rating_element.get('aria-label', '')
                    if '平均評価' in aria_label:
                        # "平均評価4.4" から "4.4" を抽出
                        rating_text = aria_label.replace('平均評価', '')
                        rating = float(rating_text)
                except ValueError:
                    rating = None

            review_count_element = detail_soup.select_one('.c-rating-total')
            if review_count_element:
                try:
                    # 「（2）」という形式から数字を抽出
                    count_text = review_count_element.text.strip().strip('（）')  # 全角括弧を削除
                    review_count = int(count_text)
                except ValueError:
                    review_count = 0

            # 商品画像URLの取得（メイン画像）
            image_url = None
            image_element = detail_soup.select_one('#photoMain img')
            if image_element and 'src' in image_element.attrs:
                image_url = image_element['src']

            # 価格情報の取得
            current_price = None
            original_price = None

            try:
                # まず通常の価格を取得
                price_element = detail_soup.select_one('.p-goods-information__price')
                discount_price_element = detail_soup.select_one('.p-goods-information__price--discount')

                # 通常価格または割引価格を取得
                target_price_element = discount_price_element or price_element

                if target_price_element:
                    try:
                        # spanタグを削除して価格テキストのみを取得
                        for span in target_price_element.find_all('span'):
                            span.decompose()

                        price_text = target_price_element.text.strip()
                        # 価格テキストから数値以外を除去（¥や,を含む全ての非数字を除去）
                        price_number = ''.join(filter(str.isdigit, price_text))
                        if price_number:
                            current_price = int(price_number)
                    except (ValueError, AttributeError) as e:
                        logging.error(f"現在価格の解析に失敗しました: {str(e)}")

                # 割引情報がある場合の処理
                discount_element = detail_soup.select_one('.p-goods-information-pricedown__rate')
                if discount_element:
                    # 割引前の価格を取得
                    original_price_element = detail_soup.select_one('.u-text-style-strike')
                    if original_price_element and original_price_element.text:
                        try:
                            original_price_text = original_price_element.text.strip()
                            # 価格テキストから数値以外を除去
                            price_number = ''.join(filter(str.isdigit, original_price_text))
                            if price_number:
                                original_price = int(price_number)
                        except (ValueError, AttributeError) as e:
                            logging.error(f"元価格の解析に失敗しました: {str(e)}")

                    # 現在価格がまだ取得できていない場合の処理
                    if not current_price and price_element and price_element.text:
                        try:
                            current_price_text = price_element.text.strip()
                            price_number = ''.join(filter(str.isdigit, current_price_text))
                            if price_number:
                                current_price = int(price_number)
                        except (ValueError, AttributeError) as e:
                            logging.error(f"割引後価格の解析に失敗しました: {str(e)}")

            except Exception as e:
                logging.error(f"価格情報の取得中に予期せぬエラーが発生: {str(e)}")

            return {
                'name': name,
                'rating': rating,
                'review_count': review_count,
                'image_url': image_url,
                'current_price': current_price,
                'original_price': original_price
            }

        except Exception as e:
            logging.error(f"商品詳細の取得エラー: {str(e)}")
            return None

    def scrape_category(self, category_url: str) -> List[Dict]:
        """
        カテゴリページから商品情報を収集
        基本情報と詳細情報を段階的に取得
        """
        products = []
        page = 1

        while len(products) < self.max_items:
            try:
                url = f"{category_url}?page={page}"
                soup = self.get_page_with_retry(url)
                if not soup:
                    break

                # カタログページからの基本情報取得
                product_elements = soup.select('.css-czyfg3.ell6q4d0')  # 適切なセレクターに変更
                if not product_elements:
                    break

                for element in product_elements:
                    if len(products) >= self.max_items:
                        break

                    # 基本情報の取得
                    basic_info = self.parse_product(element)
                    if not basic_info:
                        continue

                    # 詳細情報の取得
                    if basic_info.get('needs_details'):
                        detail_info = self.parse_product_detail(basic_info['product_url'])
                        if detail_info:
                            basic_info.update(detail_info)

                    products.append(basic_info)
                    print(f"収集済み商品数: {len(products)}/{self.max_items}")

                    # サーバー負荷軽減のための待機
                    time.sleep(random.uniform(1, 3))

                page += 1

            except Exception as e:
                logging.error(f"ページ {page} の処理中にエラー: {str(e)}")
                break

        return products

    def save_to_csv(self, products: List[Dict], filename: str = 'products.csv'):
        """
        商品データをCSVファイルに保存

        Args:
            products (List[Dict]): 保存する商品データのリスト
            filename (str): 保存するCSVファイル名
        """
        print(f"\nCSVファイルに保存中: {filename}")
        df = pd.DataFrame(products)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"CSVファイルの保存が完了しました: {len(products)} 件")
        logging.info(f"CSVファイル {filename} に {len(products)} 件の商品データを保存しました")

    def save_to_sqlite(self, products: List[Dict], db_name: str = 'zozo_products.db'):
        """
        商品データをSQLiteデータベースに保存

        Args:
            products (List[Dict]): 保存する商品データのリスト
            db_name (str): データベースファイル名
        """
        print(f"\nデータベースに保存中: {db_name}")
        conn = sqlite3.connect(db_name)
        df = pd.DataFrame(products)
        df.to_sql('products', conn, if_exists='replace', index=False)
        conn.close()
        print(f"データベースの保存が完了しました: {len(products)} 件")
        logging.info(f"データベース {db_name} に {len(products)} 件の商品データを保存しました")

    def analyze_data(self, products: List[Dict], output_dir: str = 'analysis'):
        """
        収集した商品データの分析とグラフ生成

        Args:
            products (List[Dict]): 分析する商品データのリスト
            output_dir (str): 分析結果の保存ディレクトリ

        生成する分析結果:
        1. 価格分布のヒストグラム
        2. ブランド別商品数の棒グラフ
        3. 評価と価格の相関散布図
        4. 基本統計量のJSON
        """
        print("\nデータ分析を開始します...")
        os.makedirs(output_dir, exist_ok=True)
        df = pd.DataFrame(products)

        # プロットのスタイル設定
        sns.set_style("whitegrid")
        sns.set_palette("husl")

        # 1. 価格分布の分析
        print("価格分布の分析中...")
        plt.figure(figsize=(12, 6))
        sns.histplot(data=df, x='current_price', bins=30)
        plt.title('Price Distribution', pad=15)
        plt.xlabel('Price (JPY)')
        plt.ylabel('Number of Products')
        plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/price_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()

        # 2. ブランド分析
        print("ブランド分析中...")
        plt.figure(figsize=(14, 8))
        brand_counts = df['brand'].value_counts().head(20)
        sns.barplot(x=brand_counts.values, y=brand_counts.index)
        plt.title('Products by Brand (Top 20)', pad=15)
        plt.xlabel('Number of Products')
        plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x)}'))
        plt.tight_layout()
        plt.savefig(f'{output_dir}/brand_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()

        # 3. 評価と価格の相関分析
        print("価格と評価の相関分析中...")
        plt.figure(figsize=(12, 6))

        # 相関分析に十分なデータがあるか確認
        valid_data = df.dropna(subset=['current_price', 'rating'])
        if len(valid_data) > 1:  # 相関には最低2点必要
            scatter = sns.scatterplot(data=valid_data, x='current_price', y='rating', alpha=0.6)
            plt.title('Price vs Rating Correlation', pad=15)
            plt.xlabel('Price (JPY)')
            plt.ylabel('Rating (Stars)')
            plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
            plt.xticks(rotation=45)

            # 相関係数の計算と表示
            correlation = valid_data['current_price'].corr(valid_data['rating'])
            if not pd.isna(correlation):
                plt.text(0.02, 0.95, f'Correlation: {correlation:.2f}',
                         transform=plt.gca().transAxes,
                         bbox=dict(facecolor='white', alpha=0.8))
        else:
            plt.text(0.5, 0.5, 'データが不足しています',
                     ha='center', va='center', transform=plt.gca().transAxes)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/price_rating_correlation.png', dpi=300, bbox_inches='tight')
        plt.close()

        # 4. 基本統計量の計算と保存
        print("基本統計量の計算中...")
        stats = {
            '商品数': len(df),
            '平均価格': int(df['current_price'].mean()),
            '中央価格': int(df['current_price'].median()),
            '最高価格': int(df['current_price'].max()),
            '最低価格': int(df['current_price'].min()),
            '標準偏差': int(df['current_price'].std()),
            '平均評価': round(df['rating'].mean(), 2) if not df['rating'].isna().all() else None,
            'ブランド数': df['brand'].nunique(),
            'セール商品数': len(df[df['original_price'].notna()])
        }

        # 統計情報のJSON保存
        with open(f'{output_dir}/statistics.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        # 分析結果の表示
        print("\n分析結果のサマリー:")
        for key, value in stats.items():
            print(f"{key}: {value:,}" if isinstance(value, int) else f"{key}: {value}")

    def cleanup(self):
        """
        リソースの解放処理
        - Seleniumドライバーの終了
        - その他のクリーンアップ処理
        """
        print("\nブラウザを終了します...")
        self.driver.quit()
        print("スクレイピングプロセスが完了しました。")


def main():
    """
    メイン実行関数
    スクレイピングの実行から分析までの一連の処理を制御
    """
    print("ZOZOTOWNスクレイピングを開始します...")

    # スクレイパーの初期化（最大200商品）
    scraper = ZozoScraper(max_items=200)

    try:
        # スクレイピング対象のカテゴリURLを設定
        category_url = 'https://zozo.jp/category/tops/'
        print(f"対象カテゴリ: {category_url}")

        # スクレイピングの実行
        products = scraper.scrape_category(category_url)

        if products:
            # データの保存と分析
            scraper.save_to_csv(products)
            scraper.save_to_sqlite(products)
            scraper.analyze_data(products)
            print("\nすべての処理が正常に完了しました。")
        else:
            print("\n商品データの取得に失敗しました。")

    except Exception as e:
        # エラー発生時の処理
        logging.error(f"予期せぬエラーが発生しました: {str(e)}")
        print(f"\nエラーが発生しました: {str(e)}")

    finally:
        # 終了処理（必ず実行）
        scraper.cleanup()


# スクリプトが直接実行された場合にのみmain()を実行
if __name__ == "__main__":
    main()