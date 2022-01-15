# 自動2chまとめ＆記事投稿ツール

「自動2chまとめ＆記事投稿ツール」（以降は本ツールと呼称）を既存のDeep Learning技術及び自然言語処理技術を使用して作成しました。使用言語はpythonです。

## 本ツールの作成動機

世の中には2chをまとめたサイトが大量に存在しています。また、まとめを容易にするためのツールも公開・販売されています。まとめ作業は基本的には同じ作業の繰り返しのように思い、この作業を自然言語モデルを使用して自動化できるのではと考え作りました。

## 処理方法と使用技術

本ツールではゲーム系のような同じ物事に対して継続的に同名で存在するスレッドから特定のトピックについて話している書き込みを切り出し、それをhtmlでフォーマット、wordpressへ投稿またはファイル保存しています。

主な処理は下記の流れとなっています。

1. 解析対象とするスレッドを入力
2. 各書き込みを特徴量ベクトルに変換
3. ベクトルをクラスタリングしラベル付け
4. 不適切な話題とラベリングされた書き込みを除外
5. 書き込み間のベクトルの類似度をもとに各書き込みを最も近い書き込みと関連付け
6. 関連付け情報から連結されている書き込み数が一定以上のものをまとめ記事として整形
7. まとめ記事からキーフレーズとなるワードを抽出し、タグとして利用
8. wordpressへ投稿

### 各書き込みを特徴量ベクトルに変換

sentence-transformersを用いて文章間距離を評価可能なベクトルに変換

### 特徴量ベクトルのクラスタリング

k-meansを使用

### キーフレーズとなるワードを抽出

ginza electraと呼ばれるspacyベースの日本語モデルを利用しpkeライブラリのMultipartiteRankにて書き込み群を表現するキーフレーズを生成

### 技術的な処理が行われていない項目

#### タイトル生成

タイトルは作成されたまとめ記事の最初の書き込みの1行目が使用されます。

#### サムネイル画像の決定

デフォルトとして使用される画像をいくつか用意することでそこからランダムに設定されます。
また、キーワードを設定することでまとめ記事中にそのワードが出現するとそれが設定されます。

### wordpressに関係した処理

REST API 経由にて作成した記事の投稿、タグ付け、サムネ画像のアップロードが自動でされます。

## Install方法

anacondaを使用し python 3.6.13 で環境を準備ください。それ以外は動くと思いますがわかりません。

必要なライブラリは下記となります。
```
conda install requests beautifulsoup4 jinja2
conda install -c conda-forge fake-useragent
conda install -c conda-forge selenium
conda install -c conda-forge sentence-transformers
conda install -c huggingface transformers
conda install pytorch torchvision torchaudio cudatoolkit=10.2 -c pytorch -
pip install git+https://github.com/boudinfl/pke.git
python -m nltk.downloader stopwords
pip install ginza ja_ginza_electra
pip install python-oembed
pip install googletrans==4.0.0-rc1
conda install -c conda-forge unicodedata2
conda install -c anaconda requests-toolbelt
pip install -U spacy[cuda101]
```

spacy[cuda101]に関しては自分が使用しているcudaのバージョンに合わせてください。
また、一応GPUが無いPCでも動作すると思いますが処理速度がどうなるかはわかりません。

また一部Chromeをセレニウムで操作するためChromeをインストールし、
[Chromeドライバー](https://chromedriver.chromium.org/)から最新のchromedriver.exeをダンロードし本ツールと同一フォルダに置いてください。

## 使用方法

wordpressに投稿する場合、Application Passwordsと呼ばれるプラグインをインストールし、投稿権限があるユーザーを作成。
そのユーザーのアプリケーションパスワードを取得してREST APIで操作可能にしてください。

main.py内の16行目から18行目にある`wordpress_url`, `wordpress_user`, `wordpress_password`にwordpressのURL、上記ユーザー名、取得したアプリケーションパスワードを追記。
27行目の`settings.save_outputs = True`を`False`にしてください。

単純にHTMLを生成したい場合は上記操作は必要無く、logsフォルダに出力されます。

下記コマンドで実行
```
python main.py
```

取得情報の設定は`models/summarize_settings.py`内のSummarize_Settingsを使用しています。
Summarize_Settingsを継承することで独自設定を作ることができます。設定例は`models/settings/`の中を見てください。
