import requests
import os
import json
import streamlit as st

car_info_regno_api_url = "https://api.biluppgifter.se/api/v1/vehicle/regno/{regno}"
car_info_vin_api_url = "https://api.biluppgifter.se/api/v1/vehicle/vin/{vin}"
engine_id_api_url = "https://api.biluppgifter.se/api/v1/tecdoc/regno/{regno}"
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {st.secrets['biluppgifter']['BILUPPGIFTER_API_KEY']}",
    "Content-Type": "application/json",
    "User-Agent": "My test client"
}

def get_engine_id(regno, country_code="SE"):
    """
    Get the engine ID from the Biluppgifter API using the registration number.
    """
    url = engine_id_api_url.format(regno=regno)

    params = {"country_code": country_code}
    response = requests.get(url, headers=headers, params=params)

    # # DEBUG
    # print(response.status_code, response.reason)
    # print(response.text)

    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': f"Biluppgifter API returned an error: {response.reason}"
        }

    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }

def get_car_info(regno=None, vin=None, country_code="SE"):
    """
    Get vehicle information from the Biluppgifter API using either the registration number or VIN.
    """
    engine_id = None

    # # leave out the engine_id for now
    # if regno:
    #     res = get_engine_id(regno)
    #     if res["statusCode"] != 200:
    #         return res
    #     engine_id = json.loads(res["body"])["data"]["engine_code"]

    if regno:
        url = car_info_regno_api_url.format(regno=regno)
    elif vin:
        url = car_info_vin_api_url.format(vin=vin)
    else:
        return {
            'statusCode': 400,
            'body': "Error: Registration number or VIN is required."
        }

    params = {"country_code": country_code}
    response = requests.get(url, headers=headers, params=params)

    # # DEBUG
    # print(response.status_code, response.reason)
    # print(response.text)

    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': f"Biluppgifter API returned an error: {response.reason}"
        }
    
    # add engine_id to the response
    vehicle_info = response.json()
    vehicle_info["data"]["basic"]["data"]["engine_id"] = engine_id

    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }
