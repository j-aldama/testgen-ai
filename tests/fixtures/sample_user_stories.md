# User Stories - E-Commerce Checkout

## US-001: Add to Cart
As a customer, I want to add products to my shopping cart so that I can purchase multiple items at once.

### Acceptance Criteria
- User can add any available product to the cart
- Cart displays the total number of items
- Cart shows the total price including taxes
- User can add up to 99 units of a single product

## US-002: Apply Discount Code
As a customer, I want to apply a discount code at checkout so that I can get a reduced price.

### Acceptance Criteria
- Only one discount code can be applied per order
- Discount code must be valid (not expired, not already used)
- Discount is applied to the total before taxes
- Minimum order amount of $50 required for discount codes

## US-003: Checkout Process
As a customer, I want to complete the checkout process so that I can receive my order.

### Acceptance Criteria
- User must provide shipping address
- User can select from available shipping methods
- Payment must be processed before order confirmation
- Order confirmation number is displayed after successful payment
- User receives order confirmation email
