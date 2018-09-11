pizza.py
=======
The all-in-one Dominos Pizza API Wrapper for Python.

.. image:: https://img.shields.io/badge/Python-3.x-blue.svg


Disclaimer
-----------
This is my fork of `PizzAPI <https://github.com/gamagori/pizzapi>`_.

It's heavily modified and therefore not well documented.

This version is all contained within one Python file called ``pizza.py``.


Setup
-----

1. Install Python 3.x
2. Clone or download this repository
3. Install the requirements of the repository via ``pip install -r requirements.txt``
4. Start a Python 3.x interpreter in the folder where `pizza.py` is located
5. Import the module with the command below: 

.. code-block:: python

	from pizza import *


Description
-----------

This is a Python wrapper for the Dominos Pizza API. It currently only works in the US and Canada, but other regions may be added in the future. If not, you could always fork the repository and add custom regions yourself.

Pizza.py a port of `the pizzapi node.js module <https://github.com/RIAEvangelist/node-dominos-pizza-api>`_ written by `RIAEvangelist <https://github.com/RIAEvangelist>`_.

Quick Start
-----------

Before you do anything, make sure you have imported the module with the command shown in the steps above.

First construct a ``Customer`` object and set the customer's address:

.. code-block:: python

    customer = Customer('Barack', 'Obama', 'barack@whitehouse.gov', '2024561111', '700 Pennsylvania Avenue NW, Washington, DC, 20408')

Then, find a store that will deliver to the address.

.. code-block:: python

    my_local_dominos = StoreLocator.find_closest_store_to_customer(customer)

In order to add items to your order, you'll need the items' product codes.
To find the codes, get the menu from the store, then search for items you want to add.
You can do this by asking your ``Store`` object for its ``Menu``.

.. code-block:: python

    menu = my_local_dominos.get_menu()

Then search ``menu`` with ``menu.search``. For example, running this command:

.. code-block:: python

    menu.search(Name='Coke')

Should print this to the console:

.. code-block:: text

    20BCOKE    20oz Bottle Coke®        $1.89
    20BDCOKE   20oz Bottle Diet Coke®   $1.89
    D20BZRO    20oz Bottle Coke Zero™   $1.89
    2LDCOKE    2-Liter Diet Coke®       $2.99
    2LCOKE     2-Liter Coke®            $2.99

After you've found your items' product codes, you can create an ``Order`` object add add your items:

.. code-block:: python

    order = Order.begin_customer_order(customer, my_local_dominos)
    order.add_item('P12IPAZA') # add a 12-inch pan pizza
    order.add_item('MARINARA') # with an extra marinara cup
    order.add_item('20BCOKE')  # and a 20oz bottle of coke

You can remove items as well!

.. code-block:: python

    order.remove_item('20BCOKE')

Wrap your credit card information in a ``CreditCard``:

.. code-block:: python

    card = CreditCard('4100123422343234', '0115', '777', '90210')

And that's it! Now you can place your order.

.. code-block:: python

    order.place(card)
    my_local_dominos.place_order(order, card)
