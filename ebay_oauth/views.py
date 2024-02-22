from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from oauthlib.oauth2 import OAuth2Error
from .models import Token, SellerInfo
from datetime import datetime, timedelta
import requests
import logging
from requests_oauthlib import OAuth2Session

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ebay.com"
SELLER_PROFILE_ENDPOINT = "/sell/account/v1/summary"
LISTINGS_ENDPOINT = "/sell/inventory/v1/listing"
SALES_ENDPOINT = "/sell/fulfillment/v1/order"


def ebay_login(request):
    ebay_auth_url = 'https://auth.ebay.com/oauth2/authorize'
    client_id = 'RapidRes-RapidRes-PRD-083448d6e-7b744566'
    scope = [
        'https://api.ebay.com/oauth/api_scope',
        'https://api.ebay.com/oauth/api_scope/sell.marketing.readonly',
        'https://api.ebay.com/oauth/api_scope/sell.marketing',
        'https://api.ebay.com/oauth/api_scope/sell.inventory.readonly',
        'https://api.ebay.com/oauth/api_scope/sell.inventory',
        'https://api.ebay.com/oauth/api_scope/sell.account.readonly',
        'https://api.ebay.com/oauth/api_scope/sell.account',
        'https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly',
        'https://api.ebay.com/oauth/api_scope/sell.fulfillment',
        'https://api.ebay.com/oauth/api_scope/sell.analytics.readonly',
        'https://api.ebay.com/oauth/api_scope/sell.finances',
        'https://api.ebay.com/oauth/api_scope/sell.item.draft',
        'https://api.ebay.com/oauth/api_scope/sell.item',
        'https://api.ebay.com/oauth/api_scope/sell.reputation.readonly',

    ]

    redirect_uri = 'https://ebay-integration-b1dc507216da.herokuapp.com/ebay/callback/'

    ebay = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    authorization_url, _ = ebay.authorization_url(ebay_auth_url)
    return redirect(authorization_url)\



def ebay_callback(request):
    token_url = 'https://api.ebay.com/identity/v1/oauth2/token'
    ebay = get_ebay_session(request)

    try:
        token = ebay.fetch_token(
            token_url,
            authorization_response=request.build_absolute_uri(),
            client_secret='PRD-83448d6ee35b-1b2d-49aa-9f3f-2811',
        )

        user = request.user
        platform = 'ebay'
        access_token = token['access_token']
        refresh_token = token.get('refresh_token', '')
        token_expiry = token['expires_at']

        existing_token = Token.objects.filter(user=user, platform=platform).first()

        if existing_token:
            existing_token.access_token = access_token
            existing_token.refresh_token = refresh_token
            existing_token.token_expiry = token_expiry
            existing_token.save()
        else:
            Token.objects.create(
                user=user,
                platform=platform,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=token_expiry
            )

        response = ebay.get("https://api.ebay.com/sell/account/v1/summary")
        if response.status_code == 200:
            seller_info = response.json()
            SellerInfo.objects.create(
                user=user,
                platform=platform,
                seller_info=seller_info
            )

        # Redirecting the user to the dashboard
        return redirect('dashboard')
    except OAuth2Error as e:
        logger.error(f"OAuth Error: {e}")
        return HttpResponse(f"Error: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        return HttpResponse(f"Unexpected Error: {e}")


@csrf_exempt
def ebay_notification(request):
    if request.method == 'POST':
        payload = request.body.decode('utf-8')
        logger.info("Received eBay notification payload:")
        logger.info(payload)
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=405)


def refresh_ebay_token(request):
    try:
        ebay_token = Token.objects.get(user=request.user, platform='ebay')

        if not ebay_token.refresh_token:
            return None

        token_url = 'https://api.ebay.com/identity/v1/oauth2/token'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': ebay_token.refresh_token,
        }

        response = requests.post(token_url, data=data, auth=(
            'RapidRes-RapidRes-PRD-083448d6e-7b744566', 'PRD-83448d6ee35b-1b2d-49aa-9f3f-2811'
        ))

        if response.status_code == 200:
            new_token = response.json()
            ebay_token.access_token = new_token['access_token']
            ebay_token.token_expiry = datetime.utcnow() + timedelta(seconds=new_token['expires_in'])
            ebay_token.save()
            return new_token['access_token']
        else:
            logger.error(f"Failed to refresh eBay token. Status Code: {response.status_code}")
            return None
    except Token.DoesNotExist:
        logger.error("eBay token not found for refresh.")
        return None
    except Exception as e:
        logger.exception(f"An error occurred during eBay token refresh: {e}")
        return None


def get_seller_info(request, token):
    access_token = token

    if not access_token:
        return JsonResponse({'error': 'Access token not found in the URL parameter'}, status=400)

    headers = {'Authorization': f'Bearer {access_token}'}
    seller_profile_url = "https://api.ebay.com/sell/account/v1/summary"

    logger.info(f"Requesting seller info from: {seller_profile_url}")

    try:
        response = requests.get(seller_profile_url, headers=headers)

        if response.status_code == 200:
            seller_info = response.json()
            return render(request, 'dashboard.html', {'seller_info': seller_info})
        elif response.status_code == 401:
            new_token = refresh_ebay_token(request)
            if new_token:
                headers = {'Authorization': f'Bearer {new_token}'}
                response = requests.get(seller_profile_url, headers=headers)

                if response.status_code == 200:
                    seller_info = response.json()
                    return render(request, 'dashboard.html', {'seller_info': seller_info})
                else:
                    return JsonResponse({'error': f'Failed to fetch seller information after token refresh. Status Code: {response.status_code}'}, status=response.status_code)
            else:
                return JsonResponse({'error': 'Failed to refresh eBay token'}, status=500)
        else:
            return JsonResponse({'error': f'Failed to fetch seller information. Status Code: {response.status_code}'}, status=response.status_code)
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        return JsonResponse({'error': f'An error occurred: {e}'}, status=500)


def get_listings(request):
    ebay = get_ebay_session(request)
    listings_url = BASE_URL + LISTINGS_ENDPOINT
    response = ebay.get(listings_url)

    if response.status_code == 200:
        listings_data = response.json()
        return JsonResponse(listings_data)
    else:
        return JsonResponse({'error': 'Failed to fetch listings'}, status=response.status_code)


def get_sales(request):
    ebay = get_ebay_session(request)
    sales_url = BASE_URL + SALES_ENDPOINT
    response = ebay.get(sales_url)

    if response.status_code == 200:
        sales_data = response.json()
        return JsonResponse(sales_data)
    else:
        return JsonResponse({'error': 'Failed to fetch sales'}, status=response.status_code)


def new_path_view(request):
    return HttpResponse("This is a new path!")


def dashboard(request):
    ebay = get_ebay_session(request)

    seller_info_url = BASE_URL + SELLER_PROFILE_ENDPOINT
    response_seller_info = ebay.get(seller_info_url)

    listings_url = BASE_URL + LISTINGS_ENDPOINT
    response_listings = ebay.get(listings_url)

    sales_url = BASE_URL + SALES_ENDPOINT
    response_sales = ebay.get(sales_url)
    refresh_ebay_token(request)

    return render(request, 'dashboard.html', {
        'seller_info': response_seller_info.json(),
        'listings': response_listings.json(),
        'sales': response_sales.json(),
    })


def get_ebay_session(request):
    client_id = 'RapidRes-RapidRes-PRD-083448d6e-7b744566'
    redirect_uri = 'https://ebay-integration-b1dc507216da.herokuapp.com/ebay/callback/'

    return OAuth2Session(client_id, redirect_uri=redirect_uri, token=request.session.get('ebay_token'))
