get rid of some of the test entries from purchase order, etc
layout/padding is messed up on most pages

ADMIN
Dashboard
1. clicking low stock items "view all" redirects to movements (should be low stock) ✅
2. low stock items should display in least to most stock left (0-5) ✅
3. top products should be accurate (assume that all products started off at 15 items) ✅
4. align "Kizuna collections" in the dashboard ✅
5. should cancellations still count as sales/add to the days total profit? ✅
6. get rid of top products "view all top products" button ✅
7. low stock items pictures got a little bit zoomed in ✅
8. Trying to restock doesn't actually work yet, but does redirect to purchase orders
9. ALL pages under inventory scroll when they shouldn't
10. photos are indeed zoomed out, but i can see the grey for where the image doesn't fill

Stock Movements
cashier column empty

Products
1. stock column displays "x pad" ✅
2. SKUs inaccurate ✅
3. barcodes inaccurate ✅
4. status static; needs dropdown ✅
5. add new product "brand name" section should have the option dropdown, same as category, but also have the option to be typable for new products ✅
6. check if "cost price" and "selling price" are necessary ✅
7. match status dropdown to purchase orders ✅

Purchase Orders
1. status static; add dropdown ✅
2. create purchase order button; "cashier id" should be changed to "user id" ✅
3. check if having both "line total" and "unit cost" is necessary ✅
4. products should automatically be filtered to be from the chosen supplier only
5. should have automatic price ✅
6. Purchase order currently not working
7. check that changing the status actually adds/removes stock from products
8. instead of the supplier_id, display the supplier name in the supplier column

Customers
1. give customers realistic loyalty points
2. rework customer graph segment ✅
3. Full name to be atomized ✅
4. register customer button; full name must be atomized ✅

POS terminal
1. low stock items are displayed as green; they should be red ✅
2. POS shrinks and grows according to the number of products in it, it should be a fixed size, then the items themselves within the POS "screen" should be scrollable

CASHIER
1. check what tabs should be visible, and hide everything else ✅

CUSTOMER
Products
1. make sure product quantity is deducted the moment its added to cart ✅
2. find out where/how loyalty points can actually be used, maybe add it to discounts? ✅_
3. make sure that removing an item from the cart adds it back to the product stock ✅
4. customer must be able to spend and receive points during checkout
