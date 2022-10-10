#!/usr/bin/env python
# coding: utf-8

import requests
import os
import json
import hashlib
import glob
import time
import random


# 設定ファイルから必要な情報を取得
with open("./tw_config.json") as f:
        tw_config = json.load(f)
        id = tw_config["twitter_id"]
        bearer_token = tw_config["bearer_token"]
        save_dir = tw_config["save_dir"]

# リクエスト回数を記載。1リクエストあたり約100件のツイートを取得。
request_limit = 10


def create_url():
    url = "https://api.twitter.com/2/users/{}/liked_tweets".format(id)
    tw_params = {        
        "max_results": 100,
        "expansions": "attachments.media_keys",
        "pagination_token": None,
        "media.fields": "url"
    }
    return url, tw_params


def bearer_oauth(r):
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2LikedTweetsPython"
    return r


def connect_to_endpoint(url, tw_params):
    merged_response = {
        "includes": {
            "media": []
        } 
    }
    for k in range(request_limit):
        response = requests.request("GET", url, auth=bearer_oauth, params=tw_params)
        if response.status_code != 200:
            raise Exception(
                "Request returned an error: {} {}".format(
                    response.status_code, response.text
                )
            )
        json_response = response.json()

        # 取得対象いいねの残数が0の場合、result_countは0となるため処理を抜ける
        if json_response["meta"]["result_count"] == 0:
            break
        
        # 次リクエストに必要なトークンを渡す
        tw_params["pagination_token"] = json_response["meta"]["next_token"]
        
        # response内の["includes"]["media"]配下の要素をmerged_responseに追加する
        merged_response["includes"]["media"].extend(json_response["includes"]["media"])
    
    return merged_response


def create_current_imagelist():
    files = glob.glob(save_dir + "*")
    current_imagelist = {
        "images": []
    }
    # save_dir 配下のファイル名とハッシュ値の一覧を既存ファイルリストに格納する
    for count, file in enumerate(files):         
        with open(save_dir + os.path.basename(files[count]), 'rb') as f:
            imagedata = f.read()        
        current_imagelist["images"].append({
            "filename": os.path.basename(files[count]),
            "md5": hashlib.md5(imagedata).hexdigest()
        })
    return current_imagelist


def check_hash_value(current_imagelist, tw_image_name):
    # DLした画像のハッシュを生成
    dl_image_path = save_dir + tw_image_name
    with open(dl_image_path, 'rb') as f:
        dl_image_data = f.read()
    dl_image_hash = hashlib.md5(dl_image_data).hexdigest()
    
    delete_flag = False

    # 既存ファイルリストのハッシュ値と確認し、合致する場合は削除する
    for cr_images in current_imagelist["images"]:
        if dl_image_hash == cr_images["md5"]:
            delete_flag = True
            break
    
    if delete_flag == True:
        os.remove(dl_image_path)


def get_images(merged_response, current_imagelist):
    for i, url in enumerate(merged_response["includes"]["media"]):

        # 動画ファイルはスキップ
        if merged_response["includes"]["media"][i]["type"] == "video":
            continue
        
        tw_url_list = merged_response["includes"]["media"][i]["url"].rsplit("/", 1)
        tw_image_name = tw_url_list[len(tw_url_list)-1]
        
        dl_flag = True

        # 既存ファイルリストとのファイル名チェック
        for cr_images in current_imagelist["images"]:
            
            if tw_image_name == cr_images["filename"]:
                dl_flag = False        

        # ファイル名が合致した場合はDLを実施しない
        if dl_flag == True:
            # wait処理
            wait_trigger = random.uniform(7,10)
            wait_sec = random.uniform(3,5)
            if i % int(wait_trigger) == 0:
                time.sleep(wait_sec)
            
            # ORIGサイズのURL生成
            tw_url_list = []
            tw_url_list = merged_response["includes"]["media"][i]["url"].rsplit(".", 1)
            tw_url_orig = tw_url_list[len(tw_url_list)-2] + "?format=" + tw_image_name.rsplit(".", 1)[1] + "&name=orig"
            
            # 画像DL処理
            response = requests.get(tw_url_orig)
            if response.status_code != 200:
                raise Exception(
                    "Request returned an error: {} {}".format(
                    response.status_code, response.text
                    )
                )
            else:
                tw_image = response.content
                with open(save_dir + tw_image_name, "wb") as f:
                    f.write(tw_image)
                # ハッシュ確認
                check_hash_value(current_imagelist, tw_image_name)


def main(): 
    url, tw_params = create_url()
    merged_response = connect_to_endpoint(url, tw_params)
    current_imagelist = create_current_imagelist()
    get_images(merged_response, current_imagelist)


if __name__ == "__main__":
    main()

