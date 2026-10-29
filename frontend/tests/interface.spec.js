import { test, expect } from '@playwright/test'

const passwords = {
  admin: process.env.UI_ADMIN_PASSWORD,
  waiter: process.env.UI_WAITER_PASSWORD,
  cashier: process.env.UI_CASHIER_PASSWORD,
}

async function login(page, username = 'admin') {
  test.skip(!passwords[username], 'Set the UI password environment variables to test local accounts.')
  await page.goto('/login')
  await page.getByLabel('Username', { exact: true }).fill(username)
  await page.getByLabel('Password', { exact: true }).fill(passwords[username])
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Overview', exact: true })).toBeVisible()
}

async function assertNoPageOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
}

test.afterEach(async ({ page }) => {
  if (page.isClosed()) return
  if (await page.getByRole('dialog', { name: 'Event details', exact: true }).isVisible()) {
    await page.getByRole('button', { name: 'Close event details', exact: true }).click()
  }
  const paymentDialog = page.getByRole('dialog', { name: /^(Cash|Card) payment$/ })
  if (await paymentDialog.isVisible()) {
    const cancel = paymentDialog.getByRole('button', { name: 'Cancel', exact: true })
    if (await cancel.isEnabled()) await cancel.click()
    else return
  }
  if (await page.getByRole('button', { name: 'Understood', exact: true }).isVisible()) {
    await page.getByRole('button', { name: 'Understood', exact: true }).click()
  }
  const dialog = page.getByRole('dialog', { name: 'Navigation menu' })
  if (await dialog.isVisible()) await page.getByRole('button', { name: 'Close navigation' }).click()
  const menu = page.getByRole('button', { name: 'Open navigation' })
  if (await menu.isVisible()) await menu.click()
  const signOut = page.getByRole('button', { name: 'Sign out', exact: true }).filter({ visible: true })
  if (await signOut.count()) {
    await signOut.first().click()
    await expect(page).toHaveURL(/\/login$/)
  }
})

test('login image, password visibility and empty validation', async ({ page }, testInfo) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  const asset = await page.request.get('/images/cafe-interior.png')
  expect(asset.status()).toBe(200)
  expect(asset.headers()['content-type']).toContain('image/png')
  await page.getByRole('button', { name: 'Show password' }).click()
  await expect(page.getByLabel('Password', { exact: true })).toHaveAttribute('type', 'text')
  await page.getByRole('button', { name: 'Hide password' }).click()
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveText('Please enter your username and password.')
  const panel = await page.locator('.login-panel').boundingBox()
  expect(panel.x).toBe(0)
  expect(panel.y).toBe(0)
  expect(panel.height).toBeGreaterThanOrEqual(page.viewportSize().height)
  expect(panel.width).toBe(Math.min(440, page.viewportSize().width))
  await expect(page.locator('.login-panel')).toHaveCSS('border-radius', '0px')
  await expect(page.locator('.login-panel')).toHaveCSS('box-shadow', 'none')
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('login.png'), fullPage: true })
})

test('overview displays actual operational data and refreshes', async ({ page }, testInfo) => {
  await login(page)
  await expect(page.locator('.metric-value').first()).not.toContainText('--')
  await expect(page.getByRole('region', { name: 'Operational summary' })).toHaveAttribute('aria-busy', 'false')
  const activeCount = await page.evaluate(async () => {
    const headers = { Authorization: 'Bearer ' + localStorage.getItem('bar_inventory_access') }
    let url = '/api/orders/'
    let count = 0
    while (url) {
      const response = await fetch(url, { headers })
      if (!response.ok) throw new Error('Orders API failed.')
      const data = await response.json()
      count += data.results.filter(order => ['OPEN', 'IN_CASHIER'].includes(order.status)).length
      url = data.next
    }
    return count
  })
  await expect(page.locator('.metric-value').first()).toHaveText(String(activeCount))
  await page.getByRole('button', { name: 'Refresh overview' }).click()
  await expect(page.getByRole('region', { name: 'Operational summary' })).toHaveAttribute('aria-busy', 'false')
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('overview.png'), fullPage: true })
})

test('navigation, mobile focus and management pages', async ({ page, isMobile }) => {
  await login(page)
  if (isMobile) {
    await page.getByRole('button', { name: 'Open navigation' }).click()
    const dialog = page.getByRole('dialog', { name: 'Navigation menu' })
    await expect(dialog).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await page.getByRole('button', { name: 'Open navigation' }).click()
  }
  await page.getByRole('navigation', { name: 'Main navigation' }).filter({ visible: true }).getByRole('link', { name: 'Users', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Users', exact: true })).toBeVisible()
  for (const [route, heading] of [['/admin/venues', 'Venues'], ['/admin/suppliers', 'Suppliers'], ['/inventory', 'Inventory'], ['/admin/tables', 'Tables']]) {
    await page.goto(route)
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
    await assertNoPageOverflow(page)
  }
})

test('user search, role filter and safe confirmation', async ({ page }, testInfo) => {
  await login(page)
  await page.goto('/admin/users')
  await page.getByRole('cell', { name: 'waiter', exact: true }).waitFor()
  await page.getByLabel('Search users', { exact: true }).fill('cashier')
  await expect(page.getByRole('cell', { name: 'waiter', exact: true })).toHaveCount(0)
  await expect(page.getByRole('cell', { name: 'cashier', exact: true })).toBeVisible()
  await page.getByLabel('Role', { exact: true }).selectOption('WAITER')
  await expect(page.getByText('No users match the current filters.')).toBeVisible()
  await page.getByLabel('Search users', { exact: true }).fill('')
  await page.getByLabel('Role', { exact: true }).selectOption('')
  await page.getByRole('button', { name: 'Deactivate', exact: true }).first().click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Cancel', exact: true })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Deactivate', exact: true }).first()).toBeFocused()
  await page.getByRole('button', { name: 'Edit waiter', exact: true }).click()
  await expect(page.getByLabel('Full name', { exact: false })).toHaveValue('Waiter')
  await page.getByRole('button', { name: 'Cancel', exact: true }).last().click()
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('users.png'), fullPage: true })
})

test('catalog dropdowns and price validation remain intact', async ({ page }, testInfo) => {
  await login(page)
  await page.goto('/catalog')
  await page.getByRole('button', { name: 'New product', exact: true }).click()
  await page.locator('#product-name').fill('Unsaved interface check')
  await page.locator('#product-type').selectOption('Beverage')
  await page.locator('#category').selectOption('Coffee')
  await page.locator('#purchase-price').fill('10000')
  await page.locator('#sale-price').fill('9000')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveText('Sale price cannot be lower than purchase price.')
  await expect(page.locator('#product-name')).toHaveValue('Unsaved interface check')
  await page.getByRole('button', { name: 'Cancel', exact: true }).last().click()
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('catalog.png'), fullPage: true })
})

test('room tiles, venue selector and existing order', async ({ page }, testInfo) => {
  await login(page)
  await page.goto('/room')
  await expect(page.locator('.room-tile').first()).toBeVisible()
  await expect(page.locator('.room-summary')).toContainText('Total tables')
  const options = await page.locator('#venue option').evaluateAll(nodes => nodes.map(node => node.value))
  for (const value of options) {
    await page.locator('#venue').selectOption(value)
    await expect(page.locator('.room-tile').first()).toBeVisible()
  }
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('room.png'), fullPage: true })
  const occupied = page.getByRole('button', { name: 'View order', exact: true }).first()
  if (await occupied.count()) {
    await occupied.click()
    await expect(page).toHaveURL(/\/orders\/\d+$/)
    await assertNoPageOverflow(page)
  }
})

test('empty and failed overview states', async ({ page }) => {
  await login(page)
  await page.route('**/api/{orders,products,tables,venues}/**', route => route.fulfill({ json: { results: [], next: null } }))
  await page.getByRole('button', { name: 'Refresh overview' }).click()
  await expect(page.getByText('No active orders', { exact: true })).toBeVisible()
  await expect(page.locator('.metric-value').first()).toHaveText('0')
  await page.unroute('**/api/{orders,products,tables,venues}/**')
  await page.route('**/api/orders/**', route => route.fulfill({ status: 503, json: { detail: 'Service temporarily unavailable.' } }))
  await page.getByRole('button', { name: 'Refresh overview' }).click()
  await expect(page.getByRole('alert')).toContainText('Service temporarily unavailable.')
})

test('layout fits narrow mobile, tablet and wide desktop', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop', 'Extra width checks run in the desktop project.')
  for (const width of [320, 768, 1024, 1920]) {
    await page.setViewportSize({ width, height: 1000 })
    await page.goto('/login')
    await assertNoPageOverflow(page)
  }
  await login(page)
  await expect(page.getByRole('region', { name: 'Operational summary' })).toHaveAttribute('aria-busy', 'false')
  for (const width of [320, 768, 1024, 1920]) {
    await page.setViewportSize({ width, height: 1000 })
    await assertNoPageOverflow(page)
    for (const metric of await page.locator('.metric').all()) {
      expect(await metric.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true)
    }
  }
})

test('connection dialog requires confirmation before signing out', async ({ page, context }) => {
  await login(page)
  await context.setOffline(true)
  const dialog = page.getByRole('dialog', { name: 'Connection lost', exact: true })
  await expect(dialog).toBeVisible()
  await expect(page.getByRole('button', { name: 'Understood', exact: true })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(dialog).toBeVisible()
  await context.setOffline(false)
  await expect(dialog).toBeVisible()
  await page.getByRole('button', { name: 'Understood', exact: true }).click()
  await expect(page).toHaveURL(/\/login$/)
})

test('HU22 administrator queue, venue filter and return from details', async ({ page }, testInfo) => {
  await login(page)
  await page.goto('/cashier/pending')
  await expect(page.getByRole('heading', { name: 'Pending orders', exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Payment queue' })).toHaveAttribute('aria-busy', 'false')
  await expect(page.locator('#pending-venue')).toBeVisible()
  const options = await page.locator('#pending-venue option').evaluateAll(nodes =>
    nodes.filter(node => node.value).map(node => ({ value: node.value, name: node.textContent })),
  )
  for (const option of options) {
    const loaded = page.waitForResponse(response => response.url().includes('/api/orders/pending/') && new URL(response.url()).searchParams.get('venue') === option.value)
    await page.locator('#pending-venue').selectOption(option.value)
    await loaded
    await expect(page.getByRole('region', { name: 'Payment queue' })).toHaveAttribute('aria-busy', 'false')
    for (const cell of await page.locator('.queue-table td[data-label="Venue"]').all()) await expect(cell).toHaveText(option.name)
  }
  await page.locator('#pending-venue').selectOption('')
  await expect(page.getByRole('region', { name: 'Payment queue' })).toHaveAttribute('aria-busy', 'false')
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('pending-orders.png'), fullPage: true })
  const detail = page.locator('.queue-detail').first()
  if (await detail.count()) {
    await detail.click()
    await expect(page.getByRole('heading', { name: /^Order #/ })).toBeVisible()
    await page.getByRole('link', { name: 'Back to pending orders', exact: true }).click()
    await expect(page).toHaveURL(/\/cashier\/pending$/)
  }
})

test('HU22 automatic refresh loads every page and removes old pending orders', async ({ page }) => {
  await login(page)
  let reads = 0
  let backgroundSeen = false
  const order = id => ({
    id, table_identifier: 'Table ' + id, venue_name: 'Central', waiter_name: 'Waiter',
    sent_to_cashier_at: new Date(Date.now() - 120000).toISOString(), total: 6000,
  })
  await page.route('**/api/orders/pending/**', route => {
    const query = new URL(route.request().url()).searchParams
    backgroundSeen ||= route.request().headers()['x-session-activity'] === 'background'
    if (query.get('page') === '2') return route.fulfill({ json: { results: [order(900002)], next: null } })
    reads += 1
    return route.fulfill({ json: reads === 1
      ? { results: [order(900001)], next: '/api/orders/pending/?page=2' }
      : { results: [order(900003)], next: null } })
  })
  await page.goto('/cashier/pending')
  await expect(page.getByRole('link', { name: 'View order 900002', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'View order 900003', exact: true })).toBeVisible({ timeout: 12000 })
  await expect(page.getByRole('link', { name: 'View order 900001', exact: true })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'View order 900002', exact: true })).toHaveCount(0)
  expect(backgroundSeen).toBe(true)
  await assertNoPageOverflow(page)
})

test('HU22 queue error and empty state recover without page reload', async ({ page }) => {
  await login(page)
  let fail = true
  await page.route('**/api/orders/pending/**', route => route.fulfill(fail
    ? { status: 503, json: { detail: 'Queue temporarily unavailable.' } }
    : { json: { results: [], next: null } }))
  await page.goto('/cashier/pending')
  await expect(page.getByRole('alert')).toContainText('Queue temporarily unavailable.')
  await expect(page.getByText('Queue unavailable.', { exact: true })).toBeVisible()
  fail = false
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await expect(page.getByText('No pending orders', { exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

async function mockCashOrder(page, handlePayment) {
  const order = {
    id: 900023, venue: 1, venue_name: 'Central', table: 900023, table_identifier: 'Table 1',
    waiter: 900010, waiter_name: 'Waiter', status: 'IN_CASHIER', total: 6000,
    opened_at: '2026-10-25T16:00:00Z', sent_to_cashier_at: '2026-10-25T16:10:00Z',
    items: [{ id: 1, product: 1, product_name: 'Coffee', quantity: 2, unit_price: 3000, subtotal: 6000 }],
    receipt: null,
  }
  const invoice = {
    id: 900023, number: 'V001-000001', venue: 1, sequence: 1, issued_at: '2026-10-25T16:15:00Z',
    snapshot: { order_id: order.id, venue_name: 'Central', table_identifier: 'Table 1', waiter_name: 'Waiter',
      cashier_name: 'Cashier', method: 'CASH', currency: 'COP', items: order.items, total: 6000, received_amount: 10000, change: 4000 },
  }
  await page.route('**/api/orders/900023/', route => route.fulfill({ json: order }))
  await page.route('**/api/orders/pending/**', route => route.fulfill({ json: { results: order.status === 'PAID' ? [] : [order], next: null } }))
  await page.route('**/api/invoices/900023/', route => route.fulfill({ json: invoice }))
  // Nunca se envian pagos de estas pruebas a la base de presentacion.
  await page.route('**/api/payments/**', route => handlePayment(route, order, invoice))
  return { order, invoice }
}

test('HU23 cash validation, confirmation and receipt use intercepted payments', async ({ page }, testInfo) => {
  await login(page, 'cashier')
  let requests = 0
  await mockCashOrder(page, async (route, order, invoice) => {
    requests += 1
    const data = route.request().postDataJSON()
    expect(data.order).toBe(900023)
    expect(data.received_amount).toBe(10000)
    expect(data.expected_total).toBe(6000)
    expect(data.idempotency_key).toMatch(/^[0-9a-f-]{36}$/)
    order.status = 'PAID'
    order.receipt = { id: invoice.id, number: invoice.number }
    await route.fulfill({ status: 201, json: { payment: { id: 900023, amount: 6000, change: 4000 }, invoice } })
  })
  await page.goto('/cashier/pending')
  await page.getByRole('link', { name: 'View order 900023', exact: true }).click()
  await page.getByRole('button', { name: 'Pay in cash', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Cash payment', exact: true })
  await expect(dialog).toBeVisible()
  await expect(page.getByLabel('Amount received (COP)', { exact: true })).toBeFocused()
  await page.getByLabel('Amount received (COP)', { exact: true }).fill('5000')
  await page.getByRole('button', { name: 'Confirm cash payment', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('covers the order total')
  expect(requests).toBe(0)
  await page.getByLabel('Amount received (COP)', { exact: true }).fill('10000')
  await expect(dialog.getByText('COP 4,000', { exact: true })).toBeVisible()
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('cash-payment.png'), fullPage: true })
  await dialog.locator('form').evaluate(form => { form.requestSubmit(); form.requestSubmit() })
  await expect(page).toHaveURL(/\/invoices\/900023$/)
  await expect(page.getByRole('heading', { name: 'Payment receipt', exact: true })).toBeVisible()
  expect(requests).toBe(1)
  await expect(page.locator('.receipt-number')).toHaveText('V001-000001')
  await expect(page.locator('.receipt-totals')).toContainText('COP 4,000')
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('cash-receipt.png'), fullPage: true })
  await page.getByRole('link', { name: 'Back to pending orders', exact: true }).click()
  await expect(page.getByText('No pending orders', { exact: true })).toBeVisible()
})

test('HU23 payment retry keeps its reference after a lost response', async ({ page }) => {
  await login(page)
  const keys = []
  await mockCashOrder(page, async (route, order, invoice) => {
    keys.push(route.request().postDataJSON().idempotency_key)
    if (keys.length === 1) return route.abort('failed')
    order.status = 'PAID'
    return route.fulfill({ status: 200, json: { payment: { id: 900023 }, invoice } })
  })
  await page.goto('/orders/900023')
  await page.getByRole('button', { name: 'Pay in cash', exact: true }).click()
  await page.getByLabel('Amount received (COP)', { exact: true }).fill('10000')
  await page.getByRole('button', { name: 'Confirm cash payment', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Unable to confirm payment.')
  await page.reload()
  await page.getByRole('button', { name: 'Pay in cash', exact: true }).click()
  await page.getByLabel('Amount received (COP)', { exact: true }).fill('10000')
  await page.getByRole('button', { name: 'Confirm cash payment', exact: true }).click()
  await expect(page).toHaveURL(/\/invoices\/900023$/)
  expect(keys).toHaveLength(2)
  expect(keys[1]).toBe(keys[0])
})

test('HU23 already-paid conflict reloads as read-only with receipt link', async ({ page }) => {
  await login(page, 'cashier')
  await mockCashOrder(page, (route, order, invoice) => {
    order.status = 'PAID'
    order.receipt = { id: invoice.id, number: invoice.number }
    return route.fulfill({ status: 409, json: { detail: 'This order has already been paid. Reload it to view the receipt.' } })
  })
  await page.goto('/orders/900023')
  await page.getByRole('button', { name: 'Pay in cash', exact: true }).click()
  await page.getByLabel('Amount received (COP)', { exact: true }).fill('10000')
  await page.getByRole('button', { name: 'Confirm cash payment', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('already been paid')
  await expect(page.getByRole('button', { name: 'Confirm cash payment', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Reload order', exact: true }).click()
  await expect(page.getByRole('link', { name: 'View receipt', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pay in cash', exact: true })).toHaveCount(0)
})

test('HU23 waiter cannot collect or open a receipt', async ({ page }) => {
  await login(page, 'waiter')
  let requests = 0
  await mockCashOrder(page, route => { requests += 1; return route.abort('blockedbyclient') })
  await page.goto('/orders/900023')
  await expect(page.getByRole('heading', { name: /^Order #900023/ })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pay in cash', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Pay by card', exact: true })).toHaveCount(0)
  await page.goto('/invoices/900023')
  await expect(page).toHaveURL(/\/waiter$/)
  expect(requests).toBe(0)
})

for (const [method, label] of [['CREDIT_CARD', 'Credit card'], ['DEBIT_CARD', 'Debit card']]) {
  test('HU24 ' + label + ' requires terminal confirmation and generates a card receipt', async ({ page }, testInfo) => {
    await login(page, 'cashier')
    let requests = 0
    await mockCashOrder(page, async (route, order, invoice) => {
      requests += 1
      expect(new URL(route.request().url()).pathname).toBe('/api/payments/card/')
      const payload = route.request().postDataJSON()
      expect(payload.method).toBe(method)
      expect(payload.approval_reference).toBe('APP-123456')
      expect(payload.terminal_approved).toBe(true)
      expect(payload.expected_total).toBe(6000)
      expect(payload).not.toHaveProperty('received_amount')
      expect(payload).not.toHaveProperty('card_number')
      order.status = 'PAID'
      Object.assign(invoice.snapshot, { method, approval_reference: payload.approval_reference, terminal_approved: true, received_amount: 6000, change: 0 })
      return route.fulfill({ status: 201, json: { payment: { id: 900023, method }, invoice } })
    })
    await page.goto('/orders/900023')
    await page.getByRole('button', { name: 'Pay by card', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Card payment', exact: true })
    await expect(dialog).toBeVisible()
    await expect(page.getByLabel('Approval reference', { exact: true })).toBeFocused()
    await page.getByRole('radio', { name: label, exact: true }).check()
    await page.getByRole('button', { name: 'Confirm card payment', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('terminal approval reference')
    await page.getByLabel('Approval reference', { exact: true }).fill('1234567890123456')
    await page.getByRole('button', { name: 'Confirm card payment', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('Do not enter a card number')
    await page.getByLabel('Approval reference', { exact: true }).fill(' app-123456 ')
    await page.getByRole('button', { name: 'Confirm card payment', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('approved on the external terminal')
    expect(requests).toBe(0)
    await page.getByRole('checkbox', { name: 'I confirm the payment was approved on the external terminal.', exact: true }).check()
    expect(await dialog.locator('input[type=radio]:checked').count()).toBe(1)
    await assertNoPageOverflow(page)
    await page.screenshot({ path: testInfo.outputPath('card-payment.png'), fullPage: true })
    await dialog.locator('form').evaluate(form => { form.requestSubmit(); form.requestSubmit() })
    await expect(page).toHaveURL(/\/invoices\/900023$/)
    await expect(page.getByRole('heading', { name: 'Payment receipt', exact: true })).toBeVisible()
    await expect(page.locator('.receipt-metadata')).toContainText(label)
    await expect(page.locator('.receipt-metadata')).toContainText('APP-123456')
    await expect(page.getByText('Amount received', { exact: true })).toHaveCount(0)
    await expect(page.getByText('Change', { exact: true })).toHaveCount(0)
    expect(requests).toBe(1)
    await assertNoPageOverflow(page)
    await page.screenshot({ path: testInfo.outputPath('card-receipt.png'), fullPage: true })
    await page.getByRole('link', { name: 'Back to pending orders', exact: true }).click()
    await expect(page.getByText('No pending orders', { exact: true })).toBeVisible()
  })
}

test('HU24 retry preserves reference but requires fresh terminal confirmation after reload', async ({ page }) => {
  await login(page)
  const requests = []
  await mockCashOrder(page, (route, order, invoice) => {
    const payload = route.request().postDataJSON()
    requests.push(payload)
    if (requests.length === 1) return route.abort('failed')
    Object.assign(invoice.snapshot, { method: payload.method, approval_reference: payload.approval_reference })
    return route.fulfill({ status: 200, json: { payment: { id: 900023 }, invoice } })
  })
  await page.goto('/orders/900023')
  await page.getByRole('button', { name: 'Pay by card', exact: true }).click()
  await page.getByRole('radio', { name: 'Debit card', exact: true }).check()
  await page.getByLabel('Approval reference', { exact: true }).fill('APP-123456')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Confirm card payment', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Unable to record payment.')
  await page.reload()
  await page.getByRole('button', { name: 'Pay by card', exact: true }).click()
  await page.getByRole('radio', { name: 'Debit card', exact: true }).check()
  await page.getByLabel('Approval reference', { exact: true }).fill('APP-123456')
  await expect(page.getByRole('checkbox')).not.toBeChecked()
  await page.getByRole('button', { name: 'Confirm card payment', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('approved on the external terminal')
  expect(requests).toHaveLength(1)
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Confirm card payment', exact: true }).click()
  await expect(page).toHaveURL(/\/invoices\/900023$/)
  expect(requests).toHaveLength(2)
  expect(requests[1]).toEqual(requests[0])
})

test('HU24 changing payment details resets approval and cash dialog stays separate', async ({ page }) => {
  await login(page, 'cashier')
  let requests = 0
  await mockCashOrder(page, route => { requests += 1; return route.abort('blockedbyclient') })
  await page.goto('/orders/900023')
  await page.getByRole('button', { name: 'Pay by card', exact: true }).click()
  await page.getByLabel('Approval reference', { exact: true }).fill('APP-123456')
  await page.getByRole('checkbox').check()
  await page.getByRole('radio', { name: 'Debit card', exact: true }).check()
  await expect(page.getByRole('checkbox')).not.toBeChecked()
  await page.getByRole('checkbox').check()
  await page.getByLabel('Approval reference', { exact: true }).fill('APP-654321')
  await expect(page.getByRole('checkbox')).not.toBeChecked()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Pay by card', exact: true })).toBeFocused()
  await page.getByRole('button', { name: 'Pay in cash', exact: true }).click()
  await expect(page.getByRole('dialog', { name: 'Cash payment', exact: true })).toBeVisible()
  await expect(page.getByRole('radio', { name: 'Credit card', exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  expect(requests).toBe(0)
})

test('HU24 competing payment returns a conflict without a second confirmation', async ({ page }) => {
  await login(page, 'cashier')
  await mockCashOrder(page, (route, order, invoice) => {
    order.status = 'PAID'
    order.receipt = { id: invoice.id, number: invoice.number }
    return route.fulfill({ status: 409, json: { detail: 'This order has already been paid. Reload it to view the receipt.' } })
  })
  await page.goto('/orders/900023')
  await page.getByRole('button', { name: 'Pay by card', exact: true }).click()
  await page.getByLabel('Approval reference', { exact: true }).fill('APP-123456')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Confirm card payment', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('already been paid')
  await expect(page.getByRole('button', { name: 'Confirm card payment', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Reload order', exact: true }).click()
  await expect(page.getByRole('link', { name: 'View receipt', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pay by card', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Pay in cash', exact: true })).toHaveCount(0)
})

for (const role of ['waiter', 'cashier']) {
  test('HU22 ' + role + ' queue access is enforced by server and interface', async ({ page }) => {
    await login(page, role)
    const response = await page.evaluate(async () => {
      const result = await fetch('/api/orders/pending/', { headers: { Authorization: 'Bearer ' + localStorage.getItem('bar_inventory_access') } })
      return { status: result.status, data: await result.json(), user: JSON.parse(localStorage.getItem('bar_inventory_user')) }
    })
    expect(response.status).toBe(role === 'cashier' ? 200 : 403)
    await page.goto('/cashier/pending')
    if (role === 'waiter') {
      await expect(page).toHaveURL(/\/waiter$/)
    } else {
      await expect(page.getByRole('heading', { name: 'Pending orders', exact: true })).toBeVisible()
      await expect(page.locator('#pending-venue')).toHaveCount(0)
      for (const order of response.data.results) expect(order.venue).toBe(response.user.venue)
    }
    await assertNoPageOverflow(page)
  })

  test(role + ' catalog privacy, venue scope and read-only orders', async ({ page }) => {
    await login(page, role)
    const snapshot = await page.evaluate(async () => {
      const user = JSON.parse(localStorage.getItem('bar_inventory_user'))
      const headers = { Authorization: 'Bearer ' + localStorage.getItem('bar_inventory_access') }
      async function get(path) {
        const response = await fetch('/api' + path, { headers })
        return { status: response.status, data: await response.json() }
      }
      return {
        user,
        products: await get('/products/'),
        tables: await get('/tables/'),
        orders: await get('/orders/'),
        users: await get('/users/'),
        stock: await get('/inventory/stock/'),
      }
    })
    expect(snapshot.products.status).toBe(200)
    expect(snapshot.products.data.results.length).toBeGreaterThan(0)
    for (const product of snapshot.products.data.results) expect(product).not.toHaveProperty('purchase_price')
    expect(snapshot.users.status).toBe(403)
    expect(snapshot.stock.status).toBe(role === 'waiter' ? 403 : 200)
    expect(snapshot.tables.status).toBe(200)
    expect(snapshot.orders.status).toBe(200)
    for (const table of snapshot.tables.data.results) expect(table.venue).toBe(snapshot.user.venue)
    for (const order of snapshot.orders.data.results) expect(order.venue).toBe(snapshot.user.venue)
    await page.goto('/catalog')
    await expect(page.getByRole('columnheader', { name: 'Sale price', exact: true })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Purchase', exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'New product', exact: true })).toHaveCount(0)
    if (role === 'cashier') {
      await page.goto('/inventory')
      await expect(page.getByRole('heading', { name: 'Register stock entry', exact: true })).toBeVisible()
      await expect(page.locator('#venue')).toHaveCount(0)
    } else {
      await page.goto('/inventory')
      await expect(page).toHaveURL(/\/waiter$/)
    }
    const readonly = snapshot.orders.data.results.find(order =>
      order.status !== 'OPEN' || role === 'cashier' || order.waiter !== snapshot.user.id,
    )
    if (readonly) {
      await page.goto('/orders/' + readonly.id)
      await expect(page.getByRole('heading', { name: new RegExp('Order #' + readonly.id) })).toBeVisible()
      await expect(page.getByRole('heading', { name: 'Add products', exact: true })).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Send to cashier', exact: true })).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Cancel order', exact: true })).toHaveCount(0)
    }
    await assertNoPageOverflow(page)
  })

  test(role + ' access and navigation respect existing permissions', async ({ page, isMobile }) => {
    await login(page, role)
    if (isMobile) await page.getByRole('button', { name: 'Open navigation' }).click()
    const nav = page.getByRole('navigation', { name: 'Main navigation' }).filter({ visible: true })
    await expect(nav.getByRole('link', { name: 'Users', exact: true })).toHaveCount(0)
    await expect(nav.getByRole('link', { name: 'Inventory', exact: true })).toHaveCount(role === 'cashier' ? 1 : 0)
    await expect(nav.getByRole('link', { name: 'Receipts', exact: true })).toHaveCount(role === 'cashier' ? 1 : 0)
    await expect(nav.getByRole('link', { name: 'Sales report', exact: true })).toHaveCount(role === 'cashier' ? 1 : 0)
    await expect(nav.getByRole('link', { name: 'Event log', exact: true })).toHaveCount(0)
    if (isMobile) await page.getByRole('button', { name: 'Close navigation' }).click()
    await page.goto('/admin/users')
    await expect(page).toHaveURL(new RegExp('/' + role + '$'))
    await expect(page.getByRole('heading', { name: 'Overview', exact: true })).toBeVisible()
  })
}

test('HU25 receipts panel opens immutable details, prints and preserves pagination', async ({ page }, testInfo) => {
  await login(page)
  const { invoice } = await mockCashOrder(page, route => route.abort())
  const row = { id: invoice.id, number: invoice.number, venue: 1, issued_at: invoice.issued_at,
    venue_name: invoice.snapshot.venue_name, table_identifier: 'Table 1', total: 6000, method: 'CASH' }
  await page.route('**/api/invoices/?*', route => {
    const query = new URL(route.request().url()).searchParams
    const second = query.get('page') === '2'
    return route.fulfill({ json: { count: 26, results: second ? [row] : [{ ...row, id: 900024, number: 'V001-000002' }],
      next: second ? null : '/api/invoices/?page=2', previous: second ? '/api/invoices/?page=1' : null } })
  })
  await page.goto('/invoices')
  await expect(page.getByRole('heading', { name: 'Receipts', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Previous page', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Next page', exact: true }).click()
  await expect(page.getByRole('link', { name: 'View receipt V001-000001', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Next page', exact: true })).toBeDisabled()
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('receipts-panel.png'), fullPage: true })
  await page.getByRole('link', { name: 'View receipt V001-000001', exact: true }).click()
  await expect(page.getByRole('article', { name: 'Payment receipt' })).toContainText('Central')
  await expect(page.getByRole('button', { name: /Edit|Delete|Cancel receipt/ })).toHaveCount(0)
  await page.evaluate(() => { window.print = () => { window.printRequested = true } })
  await page.getByRole('button', { name: 'Print receipt', exact: true }).click()
  expect(await page.evaluate(() => window.printRequested)).toBe(true)
  await page.emulateMedia({ media: 'print' })
  await expect(page.locator('.receipt-navigation')).toBeHidden()
  await expect(page.getByRole('article', { name: 'Payment receipt' })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('receipt-print.png'), fullPage: true })
  await page.emulateMedia({ media: 'screen' })
  await page.getByRole('link', { name: 'Back to receipts', exact: true }).click()
  await expect(page).toHaveURL(/\/invoices\?page=2$/)
  await expect(page.getByRole('link', { name: 'View receipt V001-000001', exact: true })).toBeVisible()
})

test('HU25 receipts venue filter, empty state and retry', async ({ page }) => {
  await login(page)
  let failing = true
  await page.route('**/api/venues/**', route => route.fulfill({ json: { results: [{ id: 1, name: 'Central' }, { id: 2, name: 'North' }], next: null } }))
  await page.route('**/api/invoices/?*', route => failing
    ? route.fulfill({ status: 503, json: { detail: 'Receipts temporarily unavailable.' } })
    : route.fulfill({ json: { count: 0, results: [], next: null, previous: null } }))
  const venueRequest = page.waitForRequest(request => request.url().includes('/api/venues/') && new URL(request.url()).searchParams.get('include_inactive') === 'true')
  await page.goto('/invoices')
  await venueRequest
  await expect(page.getByRole('alert')).toContainText('Receipts temporarily unavailable.')
  failing = false
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await expect(page.getByText('No receipts yet', { exact: true })).toBeVisible()
  const filtered = page.waitForRequest(request => request.url().includes('/api/invoices/') && new URL(request.url()).searchParams.get('venue') === '2')
  await page.getByLabel('Venue', { exact: true }).selectOption('2')
  await filtered
  await expect(page).toHaveURL(/\/invoices\?venue=2$/)
  await expect(page.getByRole('alert')).toHaveCount(0)
  await assertNoPageOverflow(page)
})

test('HU25 cashier panel has no venue selector', async ({ page }) => {
  await login(page, 'cashier')
  await page.goto('/invoices')
  await expect(page.getByRole('heading', { name: 'Receipts', exact: true })).toBeVisible()
  await expect(page.getByLabel('Venue', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('region', { name: 'Issued receipts', exact: true })).toHaveAttribute('aria-busy', 'false')
  await expect(page.getByRole('alert')).toHaveCount(0)
  await assertNoPageOverflow(page)
})

test('HU25 waiter cannot open the receipts panel', async ({ page }) => {
  await login(page, 'waiter')
  await page.goto('/invoices')
  await expect(page).toHaveURL(/\/waiter$/)
  await expect(page.getByRole('heading', { name: 'Overview', exact: true })).toBeVisible()
})

test('HU26 combines history filters and preserves them through pages and receipt details', async ({ page }, testInfo) => {
  await login(page)
  const { invoice } = await mockCashOrder(page, route => route.abort())
  await page.route('**/api/venues/**', route => route.fulfill({ json: { results: [{ id: 1, name: 'Central' }], next: null } }))
  await page.route('**/api/invoices/?*', route => {
    const second = new URL(route.request().url()).searchParams.get('page') === '2'
    return route.fulfill({ json: { count: 26, results: [{ id: invoice.id, number: invoice.number, venue: 1,
      venue_name: 'Central', table_identifier: 'Table 1', issued_at: invoice.issued_at, total: 6000, method: 'CASH' }],
      previous: second ? 'previous' : null, next: second ? null : 'next' } })
  })
  await page.goto('/invoices')
  await page.getByLabel('Venue', { exact: true }).selectOption('1')
  await page.getByLabel('From date', { exact: true }).fill('2026-10-01')
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-25')
  await page.getByLabel('Receipt number', { exact: true }).fill('v001')
  const applied = page.waitForRequest(request => request.url().includes('/api/invoices/') && new URL(request.url()).searchParams.get('number') === 'v001')
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click()
  const query = new URL((await applied).url()).searchParams
  expect(Object.fromEntries(query)).toEqual({ page: '1', venue: '1', start_date: '2026-10-01', end_date: '2026-10-25', number: 'v001' })
  await expect(page.getByRole('link', { name: 'View receipt V001-000001', exact: true })).toBeVisible()
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('receipt-history.png'), fullPage: true })
  if (testInfo.project.name === 'desktop') {
    for (const width of [320, 768]) {
      await page.setViewportSize({ width, height: 900 })
      await assertNoPageOverflow(page)
      await expect(page.getByRole('button', { name: 'Apply filters', exact: true })).toBeVisible()
      await page.screenshot({ path: testInfo.outputPath('receipt-history-' + width + '.png'), fullPage: true })
    }
    await page.setViewportSize({ width: 1440, height: 1000 })
  }
  await page.getByRole('button', { name: 'Next page', exact: true }).click()
  await expect(page.getByText('26 receipts · Page 2', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'View receipt V001-000001', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Payment receipt', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Back to receipts', exact: true }).click()
  await expect(page.getByLabel('Receipt number', { exact: true })).toHaveValue('v001')
  await expect(page.getByLabel('From date', { exact: true })).toHaveValue('2026-10-01')
  await expect(page.getByLabel('Through date', { exact: true })).toHaveValue('2026-10-25')
  expect(new URL(page.url()).searchParams.get('page')).toBe('2')
  await page.getByLabel('Venue', { exact: true }).selectOption('')
  await expect(page.getByText('26 receipts · Page 1', { exact: true })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('number')).toBe('v001')
})

test('HU26 validates the date range and clears empty history filters', async ({ page }) => {
  await login(page)
  let requests = 0
  await page.route('**/api/invoices/?*', route => {
    requests += 1
    return route.fulfill({ json: { count: 0, results: [], next: null, previous: null } })
  })
  await page.goto('/invoices')
  await expect(page.getByText('No receipts yet', { exact: true })).toBeVisible()
  await page.getByLabel('From date', { exact: true }).fill('2026-10-26')
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-25')
  const before = requests
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveText('End date must be on or after start date.')
  expect(requests).toBe(before)
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-27')
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click()
  await expect(page.getByText('No matching receipts', { exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await page.getByRole('button', { name: 'Clear filters', exact: true }).first().click()
  await expect(page.getByLabel('From date', { exact: true })).toHaveValue('')
  await expect(page.getByLabel('Through date', { exact: true })).toHaveValue('')
  await expect(page.getByText('No receipts yet', { exact: true })).toBeVisible()
  expect(new URL(page.url()).search).toBe('')
})

test('HU26 cashier history ignores forged venue and restores filters on reload', async ({ page }) => {
  await login(page, 'cashier')
  let lastQuery
  await page.route('**/api/invoices/?*', route => {
    lastQuery = new URL(route.request().url()).searchParams
    return route.fulfill({ json: { count: 0, results: [], next: null, previous: null } })
  })
  await page.goto('/invoices?venue=999&start_date=2020-01-01&end_date=2020-12-31&number=V001')
  await expect(page.getByText('No matching receipts', { exact: true })).toBeVisible()
  expect(lastQuery.get('venue')).toBeNull()
  expect(lastQuery.get('start_date')).toBe('2020-01-01')
  await page.reload()
  await expect(page.getByLabel('Receipt number', { exact: true })).toHaveValue('V001')
  await expect(page.getByLabel('Through date', { exact: true })).toHaveValue('2020-12-31')
  await expect(page.getByLabel('Venue', { exact: true })).toHaveCount(0)
})

function salesFixture({ legacy = false } = {}) {
  const row = { id: '1-0', invoice_id: 1, number: 'V001-000001', issued_at: '2026-10-25T17:00:00Z', venue: 1,
    venue_name: 'Central', product_id: 1, product_name: 'Coffee', category: legacy ? null : 'Coffee', quantity: 2,
    purchase_value: legacy ? null : 2000, sale_value: 6000, profit: legacy ? null : 4000 }
  return { count: 26, next: 'next', previous: null, results: [row], categories: ['Coffee'],
    summary: { sales: 156000, purchase_value: legacy ? null : 52000, profit: legacy ? null : 104000, quantity: 52,
      transactions: 26, missing_cost_lines: legacy ? 26 : 0, currency: 'COP' } }
}

test('HU27 admin sales filters, totals, pagination and full export', async ({ page }, testInfo) => {
  await login(page)
  const fixture = salesFixture()
  await page.route('**/api/venues/**', route => route.fulfill({ json: { results: [{ id: 1, name: 'Central' }], next: null } }))
  await page.route('**/api/products/**', route => route.fulfill({ json: { results: [{ id: 1, name: 'Coffee', category: 'Coffee' }], next: null } }))
  await page.route('**/api/reports/sales/?*', route => {
    const query = new URL(route.request().url()).searchParams
    if (query.get('export') === 'csv') return route.fulfill({ contentType: 'text/csv', body: 'Receipt,Sales\nV001-000001,6000\n' })
    if (query.get('export') === 'print') return route.fulfill({ json: { results: Array.from({ length: 26 }, (_, index) => ({ ...fixture.results[0], id: String(index) })), summary: fixture.summary } })
    const second = query.get('page') === '2'
    return route.fulfill({ json: { ...fixture, previous: second ? 'previous' : null, next: second ? null : 'next' } })
  })
  await page.goto('/reports/sales')
  await expect(page.getByRole('heading', { name: 'Sales report', exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Sales totals', exact: true })).toHaveCount(0)
  await page.getByLabel('From date', { exact: true }).fill('2026-10-01')
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-25')
  await page.getByLabel('Venue', { exact: true }).selectOption('1')
  await page.getByLabel('Product ID or name', { exact: true }).fill('coffee')
  await page.getByLabel('Category', { exact: true }).selectOption('Coffee')
  const generated = page.waitForRequest(request => request.url().includes('/api/reports/sales/') && new URL(request.url()).searchParams.get('product') === 'coffee')
  await page.getByRole('button', { name: 'Generate report', exact: true }).click()
  expect(Object.fromEntries(new URL((await generated).url()).searchParams)).toEqual({ page: '1', start_date: '2026-10-01', end_date: '2026-10-25', venue: '1', product: 'coffee', category: 'Coffee' })
  await expect(page.getByRole('region', { name: 'Sales results', exact: true })).toContainText('Coffee')
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('sales-report.png'), fullPage: true })
  if (testInfo.project.name === 'desktop') {
    for (const width of [320, 768]) {
      await page.setViewportSize({ width, height: 1000 })
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
      await assertNoPageOverflow(page)
      await page.screenshot({ path: testInfo.outputPath('sales-report-' + width + '.png'), fullPage: true })
    }
    await page.setViewportSize({ width: 1440, height: 1000 })
  }
  await page.getByRole('button', { name: 'Next page', exact: true }).click()
  await expect(page.getByText('26 transactions · 26 lines · Page 2', { exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Sales totals', exact: true })).toContainText('COP 156,000')
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export CSV', exact: true }).click()
  expect((await download).suggestedFilename()).toBe('sales-report.csv')
  await page.evaluate(() => { window.print = () => { window.printedLines = document.querySelectorAll('.sales-print tbody tr').length } })
  await page.getByRole('button', { name: 'Print report', exact: true }).click()
  await expect.poll(() => page.evaluate(() => window.printedLines)).toBe(26)
  await page.emulateMedia({ media: 'print' })
  await expect(page.locator('.sales-screen')).toBeHidden()
  await expect(page.getByRole('region', { name: 'Printable sales report', exact: true })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('sales-report-print.png'), fullPage: true })
  await page.emulateMedia({ media: 'screen' })
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')))
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click()
  await expect(page.getByLabel('Product ID or name', { exact: true })).toHaveValue('')
  expect(new URL(page.url()).search).toBe('')
})

test('HU27 missing historical costs stay unavailable and errors can recover', async ({ page }) => {
  await login(page)
  let failed = true
  await page.route('**/api/reports/sales/?*', route => failed
    ? route.fulfill({ status: 503, json: { detail: 'Report temporarily unavailable.' } })
    : route.fulfill({ json: salesFixture({ legacy: true }) }))
  await page.goto('/reports/sales?start_date=2026-10-01&end_date=2026-10-25')
  await expect(page.getByRole('alert')).toContainText('Report temporarily unavailable.')
  failed = false
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Historical purchase cost is missing for 26 lines.')
  await expect(page.getByRole('region', { name: 'Sales totals', exact: true })).toContainText('Not recorded')
  await page.getByLabel('From date', { exact: true }).fill('2026-10-26')
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-25')
  await page.getByRole('button', { name: 'Generate report', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('End date must be on or after start date.')
})

test('HU27 empty sales and restricted roles', async ({ page }) => {
  await login(page)
  await page.route('**/api/reports/sales/?*', route => route.fulfill({ json: { ...salesFixture(), count: 0, results: [], next: null, summary: { sales: 0, purchase_value: 0, profit: 0, quantity: 0, transactions: 0, missing_cost_lines: 0 } } }))
  await page.goto('/reports/sales?start_date=2026-10-01&end_date=2026-10-25')
  await expect(page.getByText('No records found for the selected filters.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Export CSV', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Print report', exact: true })).toBeDisabled()
})

for (const role of ['cashier', 'waiter']) {
  test('HU27 ' + role + ' cannot open administrator reports', async ({ page }) => {
    await login(page, role)
    await page.goto('/reports/sales')
    await expect(page).toHaveURL(new RegExp('/' + role + '$'))
  })
}

test('HU28 cashier own report has a fixed venue, safe fields and persistent filters', async ({ page, isMobile }, testInfo) => {
  await login(page, 'cashier')
  let lastQuery
  const fixture = { count: 26, previous: null, next: 'next', results: [{ id: '1-0', issued_at: '2026-10-25T17:00:00Z', product_id: 1,
    product_name: 'Coffee', quantity: 2, sale_value: 6000 }], summary: { sales: 156000, quantity: 52, transactions: 26, currency: 'COP' } }
  await page.route('**/api/reports/sales/own/?*', route => {
    lastQuery = new URL(route.request().url()).searchParams
    const second = lastQuery.get('page') === '2'
    return route.fulfill({ json: { ...fixture, previous: second ? 'previous' : null, next: second ? null : 'next' } })
  })
  if (isMobile) await page.getByRole('button', { name: 'Open navigation', exact: true }).click()
  await page.getByRole('navigation', { name: 'Main navigation' }).filter({ visible: true }).getByRole('link', { name: 'Sales report', exact: true }).click()
  await expect(page).toHaveURL(/\/reports\/my-sales$/)
  await expect(page.getByLabel('Venue', { exact: true })).toBeDisabled()
  await expect(page.getByLabel('Venue', { exact: true }).locator('option')).toHaveCount(1)
  await expect(page.getByLabel('Category', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Export CSV', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Print report', exact: true })).toHaveCount(0)
  await expect(page.getByText('Purchase value', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Profit', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('region', { name: 'Sales results', exact: true })).toHaveCount(0)
  await page.getByLabel('From date', { exact: true }).fill('2026-10-01')
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-25')
  await page.getByLabel('Product ID or name', { exact: true }).fill('coffee')
  await page.getByRole('button', { name: 'Generate report', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Sales results', exact: true })).toContainText('Coffee')
  expect(Object.fromEntries(lastQuery)).toEqual({ page: '1', start_date: '2026-10-01', end_date: '2026-10-25', product: 'coffee' })
  await expect(page.getByRole('region', { name: 'Sales results', exact: true }).getByRole('columnheader')).toHaveCount(4)
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('cashier-sales.png'), fullPage: true })
  if (testInfo.project.name === 'desktop') {
    for (const width of [320, 768]) {
      await page.setViewportSize({ width, height: 1000 })
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
      await assertNoPageOverflow(page)
      await page.screenshot({ path: testInfo.outputPath('cashier-sales-' + width + '.png'), fullPage: true })
    }
    await page.setViewportSize({ width: 1440, height: 1000 })
  }
  await page.getByRole('button', { name: 'Next page', exact: true }).click()
  await expect(page.getByText('26 transactions · 26 lines · Page 2', { exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Sales totals', exact: true })).toContainText('COP 156,000')
  await page.reload()
  await expect(page.getByLabel('Product ID or name', { exact: true })).toHaveValue('coffee')
  await expect(page.getByLabel('Venue', { exact: true })).toBeDisabled()
  await page.goto('/reports/my-sales?venue=999&category=Tea&export=csv&product=coffee&start_date=2026-10-01&end_date=2026-10-25')
  await expect(page.getByRole('region', { name: 'Sales results', exact: true })).toContainText('Coffee')
  expect(lastQuery.get('venue')).toBeNull()
  expect(lastQuery.get('category')).toBeNull()
  expect(lastQuery.get('export')).toBeNull()
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click()
  await expect(page.getByLabel('Venue', { exact: true })).toBeDisabled()
  await expect(page.getByLabel('Product ID or name', { exact: true })).toHaveValue('')
})

test('HU28 cashier report errors, empty state and invalid dates', async ({ page }) => {
  await login(page, 'cashier')
  let failed = true
  await page.route('**/api/reports/sales/own/?*', route => failed ? route.fulfill({ status: 503, json: { detail: 'Venue report unavailable.' } })
    : route.fulfill({ json: { count: 0, results: [], next: null, previous: null, summary: { sales: 0, quantity: 0, transactions: 0, currency: 'COP' } } }))
  await page.goto('/reports/my-sales?start_date=2026-10-01&end_date=2026-10-25')
  await expect(page.getByRole('alert')).toContainText('Venue report unavailable.')
  failed = false
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await expect(page.getByText('No records found for the selected filters.', { exact: true })).toBeVisible()
  await page.getByLabel('From date', { exact: true }).fill('2026-10-26')
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-25')
  await page.getByRole('button', { name: 'Generate report', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('End date must be on or after start date.')
})

for (const role of ['admin', 'waiter']) {
  test('HU28 ' + role + ' cannot open the cashier-only report', async ({ page }) => {
    await login(page, role)
    await page.goto('/reports/my-sales')
    await expect(page).toHaveURL(new RegExp('/' + role + '$'))
  })
}

for (const role of ['admin', 'cashier']) {
  test('HU29 ' + role + ' requires both dates and keeps role filters', async ({ page }) => {
    await login(page, role)
    const path = role === 'admin' ? '/reports/sales' : '/reports/my-sales'
    const endpoint = role === 'admin' ? '/api/reports/sales/' : '/api/reports/sales/own/'
    let requests = 0
    await page.route('**' + endpoint + '?*', route => {
      requests += 1
      return route.fulfill({ json: { count: 0, results: [], next: null, previous: null, categories: [],
        summary: { sales: 0, quantity: 0, transactions: 0, currency: 'COP', ...(role === 'admin' ? { purchase_value: 0, profit: 0, missing_cost_lines: 0 } : {}) } } })
    })
    await page.goto(path)
    await expect(page.getByLabel('From date', { exact: true })).toHaveAttribute('required', '')
    await expect(page.getByLabel('Through date', { exact: true })).toHaveAttribute('required', '')
    await page.getByRole('button', { name: 'Generate report', exact: true }).click()
    expect(requests).toBe(0)
    await page.getByLabel('From date', { exact: true }).fill('2026-10-25')
    await page.getByRole('button', { name: 'Generate report', exact: true }).click()
    expect(requests).toBe(0)
    await page.getByLabel('Through date', { exact: true }).fill('2026-10-24')
    await page.getByRole('button', { name: 'Generate report', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('End date must be on or after start date.')
    expect(requests).toBe(0)
    await page.getByLabel('Through date', { exact: true }).fill('2026-10-25')
    await page.getByRole('button', { name: 'Generate report', exact: true }).click()
    await expect(page.getByText('No records found for the selected filters.', { exact: true })).toBeVisible()
    expect(requests).toBe(1)
    await expect(page.getByLabel('Category', { exact: true })).toHaveCount(role === 'admin' ? 1 : 0)
    if (role === 'cashier') await expect(page.getByLabel('Venue', { exact: true })).toBeDisabled()
    await page.goto(path + '?start_date=2026-10-25')
    await expect(page.getByRole('alert')).toContainText('Both start and end dates are required.')
    expect(requests).toBe(1)
    await page.getByRole('button', { name: 'Clear filters', exact: true }).click()
    await expect(page.getByRole('region', { name: 'Sales totals', exact: true })).toHaveCount(0)
    await expect(page.getByLabel('From date', { exact: true })).toHaveValue('')
    expect(requests).toBe(1)
  })

  test('HU29 ' + role + ' live report renders in less than two seconds', async ({ page }) => {
    await login(page, role)
    const path = role === 'admin' ? '/reports/sales' : '/reports/my-sales'
    const endpoint = role === 'admin' ? '/api/reports/sales/' : '/api/reports/sales/own/'
    const response = page.waitForResponse(item => new URL(item.url()).pathname === endpoint && item.request().method() === 'GET')
    const started = Date.now()
    await page.goto(path + '?start_date=2010-01-01&end_date=2026-12-31')
    expect((await response).status()).toBe(200)
    await expect(page.getByRole('region', { name: 'Sales totals', exact: true })).toBeVisible()
    const elapsed = Date.now() - started
    console.log('HU29 live ' + role + ' report (navigation to totals): ' + elapsed + 'ms')
    expect(elapsed).toBeLessThan(2000)
    await assertNoPageOverflow(page)
  })
}

function auditFixture({ legacy = false, id = 900030 } = {}) {
  return { id, username: 'cashier', event_type: 'ORDER_OPENED', event_type_label: 'Order opened', entity: 'Order', entity_id: '42',
    venue: legacy ? null : 1, venue_name: legacy ? '' : 'Central', venue_recorded: !legacy, created_at: '2026-10-25T17:00:00.123456Z' }
}
const auditTypes = [{ value: 'ORDER_OPENED', label: 'Order opened' }, { value: 'PAYMENT_PROCESSED', label: 'Payment processed' }]

test('HU30 admin event log combines filters and opens immutable event details', async ({ page, isMobile }, testInfo) => {
  await login(page)
  await page.route('**/api/venues/**', route => route.fulfill({ json: { results: [{ id: 1, name: 'Central' }], next: null } }))
  await page.route('**/api/audit/events/?*', route => {
    const query = new URL(route.request().url()).searchParams
    const second = query.get('page') === '2'
    return route.fulfill({ json: { count: 26, previous: second ? 'previous' : null, next: second ? null : 'next',
      event_types: auditTypes, results: [auditFixture({ legacy: second || query.get('venue') === '__unrecorded__', id: second ? 900031 : 900030 })] } })
  })
  await page.route('**/api/audit/events/900031/', route => route.fulfill({ json: { ...auditFixture({ id: 900031, legacy: true }),
    description: 'Opened order 42.\n<img src=x onerror="window.auditInjected=true">', ip_address: '127.0.0.1' } }))
  if (isMobile) await page.getByRole('button', { name: 'Open navigation', exact: true }).click()
  await page.getByRole('navigation', { name: 'Main navigation' }).filter({ visible: true }).getByRole('link', { name: 'Event log', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Event log', exact: true })).toBeVisible()
  await page.getByLabel('From date', { exact: true }).fill('2026-10-01')
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-25')
  await page.getByLabel('Username', { exact: true }).fill('cash')
  await page.getByLabel('Event type', { exact: true }).selectOption('ORDER_OPENED')
  await page.getByLabel('Venue', { exact: true }).selectOption('1')
  const request = page.waitForRequest(item => item.url().includes('/api/audit/events/') && new URL(item.url()).searchParams.get('username') === 'cash')
  await page.getByRole('button', { name: 'Search events', exact: true }).click()
  expect(Object.fromEntries(new URL((await request).url()).searchParams)).toEqual({ start_date: '2026-10-01', end_date: '2026-10-25', username: 'cash', event_type: 'ORDER_OPENED', venue: '1', page: '1' })
  await expect(page.getByRole('button', { name: 'View event 900030', exact: true })).toBeVisible()
  await assertNoPageOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('audit-log.png'), fullPage: true })
  if (testInfo.project.name === 'desktop') {
    for (const width of [320, 768]) {
      await page.setViewportSize({ width, height: 1000 })
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
      await assertNoPageOverflow(page)
      await page.screenshot({ path: testInfo.outputPath('audit-log-' + width + '.png'), fullPage: true })
    }
    await page.setViewportSize({ width: 1440, height: 1000 })
  }
  await page.getByRole('button', { name: 'Next page', exact: true }).click()
  await page.getByRole('button', { name: 'View event 900031', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Event details', exact: true })
  await expect(dialog).toContainText('2026-10-25T17:00:00.123456Z')
  await expect(dialog).toContainText('Not recorded')
  await expect(dialog).toContainText('<img src=x onerror=')
  expect(await page.evaluate(() => window.auditInjected)).toBeUndefined()
  await expect(dialog.getByRole('button', { name: /Edit|Delete|Save/ })).toHaveCount(0)
  await page.screenshot({ path: testInfo.outputPath('audit-event-detail.png'), fullPage: true })
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'View event 900031', exact: true })).toBeFocused()
  await page.reload()
  await expect(page.getByLabel('Username', { exact: true })).toHaveValue('cash')
  expect(new URL(page.url()).searchParams.get('page')).toBe('2')
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click()
  await expect(page.getByText('26 events · Page 1', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Username', { exact: true })).toHaveValue('')
})

test('HU30 audit list and detail errors recover and empty filters are explicit', async ({ page }) => {
  await login(page)
  let listFailed = true
  let detailFailed = true
  let empty = false
  await page.route('**/api/audit/events/?*', route => listFailed ? route.fulfill({ status: 503, json: { detail: 'Audit log unavailable.' } })
    : route.fulfill({ json: { count: empty ? 0 : 1, previous: null, next: null, event_types: auditTypes, results: empty ? [] : [auditFixture()] } }))
  await page.route('**/api/audit/events/900030/', route => detailFailed ? route.fulfill({ status: 503, json: { detail: 'Event details unavailable.' } })
    : route.fulfill({ json: { ...auditFixture(), description: 'Opened order 42.', ip_address: null } }))
  await page.goto('/audit/events')
  await expect(page.getByRole('alert')).toContainText('Audit log unavailable.')
  listFailed = false
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await page.getByRole('button', { name: 'View event 900030', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Event details unavailable.')
  detailFailed = false
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await expect(page.getByRole('dialog', { name: 'Event details', exact: true })).toContainText('Opened order 42.')
  await page.getByRole('button', { name: 'Close event details', exact: true }).click()
  await page.getByLabel('From date', { exact: true }).fill('2026-10-26')
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-25')
  await page.getByRole('button', { name: 'Search events', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('End date must be on or after start date.')
  await page.getByLabel('Through date', { exact: true }).fill('2026-10-27')
  empty = true
  await page.getByRole('button', { name: 'Search events', exact: true }).click()
  await expect(page.getByText('No events found for the selected filters.', { exact: true })).toBeVisible()
})

for (const role of ['cashier', 'waiter']) {
  test('HU30 ' + role + ' cannot access the audit module', async ({ page }) => {
    await login(page, role)
    await page.goto('/audit/events')
    await expect(page).toHaveURL(new RegExp('/' + role + '$'))
  })
}

test('HU30 live audit log renders in less than two seconds', async ({ page }) => {
  await login(page)
  const response = page.waitForResponse(item => new URL(item.url()).pathname === '/api/audit/events/' && item.request().method() === 'GET')
  const started = Date.now()
  await page.goto('/audit/events')
  expect((await response).status()).toBe(200)
  await expect(page.getByRole('region', { name: 'Audit events', exact: true })).toHaveAttribute('aria-busy', 'false')
  const elapsed = Date.now() - started
  console.log('HU30 live audit log (navigation to events): ' + elapsed + 'ms')
  expect(elapsed).toBeLessThan(2000)
  await assertNoPageOverflow(page)
})
