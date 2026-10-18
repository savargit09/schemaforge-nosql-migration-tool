SELECT o.order_id, o.order_date, o.status, oi.quantity, p.name, oi.unit_price
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.customer_id = 3 ORDER BY o.order_date DESC;

SELECT c.customer_id, c.name, o.order_id, o.order_total
FROM customers c JOIN orders o ON c.customer_id = o.customer_id
WHERE c.customer_id = 3 ORDER BY o.order_date DESC;

SELECT p.product_id, p.name, SUM(oi.quantity) AS units_sold
FROM products p JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.name ORDER BY units_sold DESC;

SELECT order_id, status, order_date FROM orders
WHERE status = 'SHIPPED' ORDER BY order_date DESC;
