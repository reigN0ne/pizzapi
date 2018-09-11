# Pizza.py
# Written by iCrazyBlaze, original fork by Jarvis Johnson
# Original API by Gamagori and RIAEvangelist
# Last updated 7/9/2018

import requests
import xmltodict
import pytest
import mock
import re

# TODO: Add more countries
COUNTRY_USA = 'us'
COUNTRY_CANADA = 'ca'


# TODO: Find out why this occasionally hangs
# TODO: Can we wrap this up, so the callers don't have to worry about the 
    # complexity of two types of requests? 
def request_json(url, **kwargs):
    """Send a GET request to one of the API endpoints that returns JSON.

    Send a GET request to an endpoint, ideally a URL from the urls module.
    The endpoint is formatted with the kwargs passed to it.

    This will error on an invalid request (requests.Request.raise_for_status()), but will otherwise return a dict.
    """
    r = requests.get(url.format(**kwargs))
    r.raise_for_status()
    return r.json()


def request_xml(url, **kwargs):
    """Send an XML request to one of the API endpoints that returns XML.
    
    This is in every respect identical to request_json. 
    """
    r = requests.get(url.format(**kwargs))
    r.raise_for_status()
    return xmltodict.parse(r.text)




# TODO: Add add_coupon and remove_coupon methods
class Order(object):
    """Core interface to the payments API.

    The Order is perhaps the second most complicated class - it wraps
    up all the logic for actually placing the order, after we've
    determined what we want from the Menu. 
    """
    def __init__(self, store, customer, country=COUNTRY_USA):
        self.store = store
        self.menu = Menu.from_store(store_id=store.id, country=country)
        self.customer = customer
        self.address = customer.address
        self.urls = Urls(country)
        self.data = {
            'Address': {'Street': self.address.street,
                        'City': self.address.city,
                        'Region': self.address.region,
                        'PostalCode': self.address.zip,
                        'Type': 'House'},
            'Coupons': [], 'CustomerID': '', 'Extension': '',
            'OrderChannel': 'OLO', 'OrderID': '', 'NoCombine': True,
            'OrderMethod': 'Web', 'OrderTaker': None, 'Payments': [],
            'Products': [], 'Market': '', 'Currency': '',
            'ServiceMethod': 'Delivery', 'Tags': {}, 'Version': '1.0',
            'SourceOrganizationURI': 'order.dominos.com', 'LanguageCode': 'en',
            'Partners': {}, 'NewUser': True, 'metaData': {}, 'Amounts': {},
            'BusinessDate': '', 'EstimatedWaitMinutes': '',
            'PriceOrderTime': '', 'AmountsBreakdown': {}
            }

    @staticmethod
    def begin_customer_order(customer, store, country=COUNTRY_USA):
        return Order(store, customer, country=country)

    def __repr__(self):
        return "An order for {} with {} items in it\n".format(
            self.customer.first_name,
            len(self.data['Products']) if self.data['Products'] else 'no',
        )

    # TODO: Implement item options
    # TODO: Add exception handling for KeyErrors
    def add_item(self, code, qty=1, options=[]):
        item = self.menu.variants[code]
        item.update(ID=1, isNew=True, Qty=qty, AutoRemove=False)
        self.data['Products'].append(item)
        return item

    # TODO: Raise Exception when index isn't found
    def remove_item(self, code):
        codes = [x['Code'] for x in self.data['Products']]
        return self.data['Products'].pop(codes.index(code))

    def add_coupon(self, code, qty=1):
        item = self.menu.variants[code]
        item.update(ID=1, isNew=True, Qty=qty, AutoRemove=False)
        self.data['Coupons'].append(item)
        return item

    def remove_coupon(self, code):
        codes = [x['Code'] for x in self.data['Coupons']]
        return self.data['Coupons'].pop(codes.index(code))

    def _send(self, url, merge):
        self.data.update(
            StoreID=self.store.id,
            Email=self.customer.email,
            FirstName=self.customer.first_name,
            LastName=self.customer.last_name,
            Phone=self.customer.phone,
        )

        for key in ('Products', 'StoreID', 'Address'):
            if key not in self.data or not self.data[key]:
                raise Exception('order has invalid value for key "%s"' % key)

        headers = {
            'Referer': 'https://order.dominos.com/en/pages/order/',
            'Content-Type': 'application/json'
        }

        r = requests.post(url=url, headers=headers, json={'Order': self.data})
        r.raise_for_status()
        json_data = r.json()

        if merge:
            for key, value in json_data['Order'].items():
                if value or not isinstance(value, list):
                    self.data[key] = value
        return json_data

    # TODO: Figure out if this validates anything that self.urls.price_url() does not
    def validate(self):
        response = self._send(self.urls.validate_url(), True)
        return response['Status'] != -1

    # TODO: Actually test this
    def place(self, card=False):
        self.pay_with(card)
        response = self._send(self.urls.place_url(), False)
        return response

    # TODO: Add self.price() and update whenever called and items were changed
    def pay_with(self, card=False):
        """Use this instead of self.place when testing"""
        # get the price to check that everything worked okay
        response = self._send(self.urls.price_url(), True)
        
        if response['Status'] == -1:
            raise Exception('get price failed: %r' % response)

        if card == False:
            self.data['Payments'] = [
                {
                    'Type': 'Cash',
                }
            ]
        else:
            self.data['Payments'] = [
                {
                    'Type': 'CreditCard',
                    'Expiration': card.expiration,
                    'Amount': self.data['Amounts'].get('Customer', 0),
                    'CardType': card.card_type,
                    'Number': int(card.number),
                    'SecurityCode': int(card.cvv),
                    'PostalCode': int(card.zip)
                }
            ]

        return response
		
		
		

class Address(object):
    """Create an address, for finding stores and placing orders.

    The Address object describes a street address in North America (USA or
    Canada, for now). Callers can use the Address object's methods to find
    the closest or nearby stores from the API. 

    Attributes:
        street (String): Street address
        city (String): North American city
        region (String): North American region (state, province, territory)
        zip (String): North American ZIP code
        urls (String): Country-specific URLs
        country (String): Country
    """

    def __init__(self, street, city, region='', zip='', country=COUNTRY_USA, *args):
        self.street = street.strip()
        self.city = city.strip()
        self.region = region.strip()
        self.zip = str(zip).strip()
        self.urls = Urls(country)
        self.country = country

    def __repr__(self):
        return ", ".join([self.street, self.city, self.region, self.zip])
 
    @property
    def data(self):
        return {'Street': self.street, 'City': self.city,
                'Region': self.region, 'PostalCode': self.zip}

    @property
    def line1(self):
        return '{Street}'.format(**self.data)

    @property
    def line2(self):
        return '{City}, {Region}, {PostalCode}'.format(**self.data)

    def nearby_stores(self, service='Delivery'):
        """Query the API to find nearby stores.

        nearby_stores will filter the information we receive from the API
        to exclude stores that are not currently online (!['IsOnlineNow']),
        and stores that are not currently in service (!['ServiceIsOpen']).
        """
        data = request_json(self.urls.find_url(), line1=self.line1, line2=self.line2, type=service)
        return [Store(x, self.country) for x in data['Stores']
                if x['IsOnlineNow'] and x['ServiceIsOpen'][service]]

    def closest_store(self, service='Delivery'):
        stores = self.nearby_stores(service=service)
        if not stores:
            raise Exception('No local stores are currently open')
        return stores[0]

class Coupon(object):
    """Loose representation of a coupon - no logic. 

    This is a coupon - you can add it to an Order (order.add_item) and,
    if it fits, get some money off your purchase. I think. 

    This is another thing that's worth exploring - there are some sweet 
    coupons that would be awful without the coupon. 
    """
    def __init__(self, code, quantity=1):
        self.code = code
        self.quantity = quantity
        self.id = 1
        self.is_new = True


class Customer:
    """The Customer who orders a pizza."""

    def __init__(self, fname='', lname='', email='', phone='', address=None):
        self.first_name = fname.strip()
        self.last_name = lname.strip()
        self.email = email.strip()
        self.phone = str(phone).strip()
        self.address = Address(*address.split(','))

    def __repr__(self):
        return "Name: {} {}\nEmail: {}\nPhone: {}\nAddress: {}".format(
            self.first_name,
            self.last_name,
            self.email,
            self.phone,
            self.address,
        )



# TODO: Get rid of this class
class MenuCategory(object):
    def __init__(self, menu_data={}, parent=None):
        self.menu_data = menu_data
        self.subcategories = []
        self.products = []
        self.parent = parent
        self.code = menu_data['Code']
        self.name = menu_data['Name']

    def get_category_path(self):
        path = '' if not self.parent else self.parent.get_category_path()
        return path + self.code


# TODO: Get rid of this class
class MenuItem(object):
    def __init__(self, data={}):
        self.code = data['Code']
        self.name = data['Name']
        self.menu_data = data
        self.categories = []


class Menu(object):
    """The Menu is our primary interface with the API. 

    This is far and away the most complicated class - it wraps up most of
    the logic that parses the information we get from the API.

    Next time I get pizza, there is a lot of work to be done in 
    documenting this class.
    """
    def __init__(self, data={}, country=COUNTRY_USA):
        self.variants = data.get('Variants', {})
        self.menu_by_code = {}
        self.root_categories = {}
        self.country = COUNTRY_USA

        if self.variants:
            self.products = self.parse_items(data['Products'])
            self.coupons = self.parse_items(data['Coupons'])
            self.preconfigured = self.parse_items(data['PreconfiguredProducts'])
            for key, value in data['Categorization'].items():
                self.root_categories[key] = self.build_categories(value)

    @classmethod
    def from_store(cls, store_id, lang='en', country=COUNTRY_USA):
        response = request_json(Urls(country).menu_url(), store_id=store_id, lang=lang)
        menu = cls(response)
        return menu

    # TODO: Reconfigure structure to show that Codes (not ProductCodes) matter
    def build_categories(self, category_data, parent=None):
        category = MenuCategory(category_data, parent)
        for subcategory in category_data['Categories']:
            new_subcategory = self.build_categories(subcategory, category)
            category.subcategories.append(new_subcategory)
        for product_code in category_data['Products']:
            if product_code not in self.menu_by_code:
                raise Exception('PRODUCT NOT FOUND: %s %s' % (product_code, category.code))
            product = self.menu_by_code[product_code]
            category.products.append(product)
            product.categories.append(category)
        return category

    def parse_items(self, parent_data):
        items = []
        for code in parent_data.keys():
            obj = MenuItem(parent_data[code])
            self.menu_by_code[obj.code] = obj
            items.append(obj)
        return items

    # TODO: Print codes that can actually be used to order items
    def display(self):
        def print_category(category, depth=1):
            indent = "  " * (depth + 1)
            if len(category.products) + len(category.subcategories) > 0:
                print(indent + category.name)
                for subcategory in category.subcategories:
                    print_category(subcategory, depth + 1)
                for product in category.products:
                    print(indent + "  [%s]" % product.code, product.name)
        print("************ Coupon Menu ************")
        print_category(self.root_categories['Coupons'])
        print("\n************ Preconfigured Menu ************")
        print_category(self.root_categories['PreconfiguredProducts'])
        print("\n************ Regular Menu ************")
        print_category(self.root_categories['Food'])

    # TODO: Find more pythonic way to format the menu
    # TODO: Format the menu after the variants have been filtered
    # TODO: Return the search results and print in different method
    # TODO: Import fuzzy search module or allow lists as search conditions
    def search(self, **conditions):
        max_len = lambda x: 2 + max(len(v[x]) for v in list(self.variants.values()))
        for v in self.variants.values():
            v['Toppings'] = dict(x.split('=', 1) for x in v['Tags']['DefaultToppings'].split(',') if x)
            if all(y in v.get(x, '') for x, y in conditions.items()):
                print(v['Code'], end=' ')
                print(v['Name'], end=' ')
                print('$' + v['Price'])
                #print(v['SizeCode'], end=' ')
                #print(v['ProductCode'], end=' ')
                #print(v['Toppings'])



class CreditCard(object):
    """A CreditCard represents a credit card.

    There's some sweet logic in here to make sure that the type of card
    you passed is valid. 
    """
    def __init__(self, number='', expiration='', cvv='', zip=''):
        self.name = ''
        self.number = str(number).strip()
        self.card_type = self.find_type()
        self.expiration = str(expiration).strip()
        self.cvv = str(cvv).strip()
        self.zip = str(zip).strip()

    def __repr__(self):
        return "Credit Card with last four #{}".format(self.number[-4:])

    def validate(self):
        is_valid = self.number and self.card_type and self.expiration
        is_valid &= re.match(r'^[0-9]{3,4}$', self.cvv)
        is_valid &= re.match(r'^[0-9]{5}(?:-[0-9]{4})?$', self.zip)
        return is_valid

    def find_type(self):
        patterns = {'VISA': r'^4[0-9]{12}(?:[0-9]{3})?$',
                    'MASTERCARD': r'^5[1-5][0-9]{14}$',
                    'AMEX': r'^3[47][0-9]{13}$',
                    'DINERS': r'^3(?:0[0-5]|[68][0-9])[0-9]{11}$',
                    'DISCOVER': r'^6(?:011|5[0-9]{2})[0-9]{12}$',
                    'JCB': r'^(?:2131|1800|35\d{3})\d{11}$',
                    'ENROUTE': r'^(?:2014|2149)\d{11}$'}
        return next((card_type for card_type, pattern in list(patterns.items())
                     if re.match(pattern, self.number)), '')





class Store(object):
    """The interface to the Store API

    You can use this to find store information about stores near an
    address, or to find the closest store to an address. 
    """
    def __init__(self, data={}, country=COUNTRY_USA):
        self.id = str(data.get('StoreID', -1))
        self.country = country
        self.urls = Urls(country)
        self.data = data

    def __repr__(self):
        return "Store #{}\nAddress: {}\n\nOpen Now: {}".format(
            self.id,
            self.data['AddressDescription'],
            'Yes' if self.data.get('IsOpen', False) else 'No',
        )

    def get_details(self):
        details = request_json(self.urls.info_url(), store_id=self.id)
        return details
    
    def place_order(self, order, card):
        print('Order placed for {}'.format(order.customer.first_name))
        return order.place(card=card)

    def get_menu(self, lang='en'):
        response = request_json(self.urls.menu_url(), store_id=self.id, lang=lang)
        menu = Menu(response, self.country)
        return menu


class StoreLocator(object):
    @classmethod
    def __repr__(self):
        return 'I locate stores and nothing else'

    @staticmethod
    def nearby_stores(address, service='Delivery'):
        """Query the API to find nearby stores.

        nearby_stores will filter the information we receive from the API
        to exclude stores that are not currently online (!['IsOnlineNow']),
        and stores that are not currently in service (!['ServiceIsOpen']).
        """
        data = request_json(address.urls.find_url(), line1=address.line1, line2=address.line2, type=service)
        return [Store(x, address.country) for x in data['Stores']
                if x['IsOnlineNow'] and x['ServiceIsOpen'][service]]

    @staticmethod
    def find_closest_store_to_customer(customer, service='Delivery'):
        stores = StoreLocator.nearby_stores(customer.address, service=service)
        if not stores:
            raise Exception('No local stores are currently open')
        return stores[0]




def track_by_phone(phone, country=COUNTRY_USA):
    """Query the API to get tracking information.

    Not quite sure what this gets you - problem to solve for next time I get pizza. 
    """
    phone = str(phone).strip()
    data = request_xml(
        Urls(country).track_by_phone(), 
        phone=phone
    )['soap:Envelope']['soap:Body']

    response = data['GetTrackerDataResponse']['OrderStatuses']['OrderStatus']

    return response


def track_by_order(store_id, order_key, country=COUNTRY_USA):
    """Query the API to get tracking information.
    """
    return request_json(
        Urls(country).track_by_order(),
        store_id=store_id,
        order_key=order_key
    )

	

class Urls(object):
    """URLs for doing different things to the API.

    This initializes some dicts that contain country-unique information
    on how to interact with the API, and some getter methods for getting
    to that information. These are handy to pass as a first argument to
    pizzapy.utils.request_[xml|json]. 
    """
    def __init__(self, country=COUNTRY_USA):

        self.country = country
        self.urls = {
            COUNTRY_USA: {
                'find_url' : 'https://order.dominos.com/power/store-locator?s={line1}&c={line2}&type={type}',
                'info_url' : 'https://order.dominos.com/power/store/{store_id}/profile',
                'menu_url' : 'https://order.dominos.com/power/store/{store_id}/menu?lang={lang}&structured=true',
                'place_url' : 'https://order.dominos.com/power/place-order',
                'price_url' : 'https://order.dominos.com/power/price-order',
                'track_by_order' : 'https://trkweb.dominos.com/orderstorage/GetTrackerData?StoreID={store_id}&OrderKey={order_key}',
                'track_by_phone' : 'https://trkweb.dominos.com/orderstorage/GetTrackerData?Phone={phone}',
                'validate_url' : 'https://order.dominos.com/power/validate-order',
                'coupon_url' : 'https://order.dominos.com/power/store/{store_id}/coupon/{couponid}?lang={lang}',
            },
            COUNTRY_CANADA: {
                'find_url' : 'https://order.dominos.ca/power/store-locator?s={line1}&c={line2}&type={type}',
                'info_url' : 'https://order.dominos.ca/power/store/{store_id}/profile',
                'menu_url' : 'https://order.dominos.ca/power/store/{store_id}/menu?lang={lang}&structured=true',
                'place_url' : 'https://order.dominos.ca/power/place-order',
                'price_url' : 'https://order.dominos.ca/power/price-order',
                'track_by_order' : 'https://trkweb.dominos.ca/orderstorage/GetTrackerData?StoreID={store_id}&OrderKey={order_key}',
                'track_by_phone' : 'https://trkweb.dominos.ca/orderstorage/GetTrackerData?Phone={phone}',
                'validate_url' : 'https://order.dominos.ca/power/validate-order',
                'coupon_url' : 'https://order.dominos.ca/power/store/{store_id}/coupon/{couponid}?lang={lang}',
            }
        }
    
    def find_url(self):
        return self.urls[self.country]['find_url']
    
    def info_url(self):
        return self.urls[self.country]['info_url']

    def menu_url(self):
        return self.urls[self.country]['menu_url']

    def place_url(self):
        return self.urls[self.country]['place_url']

    def price_url(self):
        return self.urls[self.country]['price_url']

    def track_by_order(self):
        return self.urls[self.country]['track_by_order']

    def track_by_phone(self):
        return self.urls[self.country]['track_by_phone']
    
    def validate_url(self):
        return self.urls[self.country]['validate_url']
    
    def coupon_url(self):
        return self.urls[self.country]['coupon_url']
    
    
if __name__ == "__main__":
    exit("This script should not be run directly. Use 'from pizza import *' to import and use the API in Python 3.")

					 
