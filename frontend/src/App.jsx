import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider } from './context/AuthContext'
import HomePage from './pages/HomePage'
import PendingOrdersPage from './pages/PendingOrdersPage'
import InvoicePage from './pages/InvoicePage'
import InvoicesPage from './pages/InvoicesPage'
import SalesReportPage from './pages/SalesReportPage'
import AuditEventsPage from './pages/AuditEventsPage'
import LoginPage from './pages/LoginPage'
import InventoryPage from './pages/InventoryPage'
import OrderDetailPage from './pages/OrderDetailPage'
import ProductsPage from './pages/ProductsPage'
import RoomPage from './pages/RoomPage'
import SuppliersPage from './pages/SuppliersPage'
import TablesPage from './pages/TablesPage'
import UsersPage from './pages/UsersPage'
import VenuesPage from './pages/VenuesPage'

/**
 * Raíz de la aplicación.
 * Cada rol es redirigido a su menú principal tras iniciar sesión (HU01).
 */
export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/audit/events" element={<ProtectedRoute roles={['ADMIN']}><AuditEventsPage /></ProtectedRoute>} />
        <Route path="/reports/my-sales" element={<ProtectedRoute roles={['CASHIER']}><SalesReportPage /></ProtectedRoute>} />
        <Route path="/reports/sales" element={<ProtectedRoute roles={['ADMIN']}><SalesReportPage /></ProtectedRoute>} />
        <Route path="/invoices" element={<ProtectedRoute roles={['ADMIN', 'CASHIER']}><InvoicesPage /></ProtectedRoute>} />
        <Route path="/invoices/:invoiceId" element={<ProtectedRoute roles={['ADMIN', 'CASHIER']}><InvoicePage /></ProtectedRoute>} />
        <Route path="/cashier/pending" element={<ProtectedRoute roles={['ADMIN', 'CASHIER']}><PendingOrdersPage /></ProtectedRoute>} />
        <Route path="/login" element={<LoginPage />} />

        <Route
          path="/admin"
          element={
            <ProtectedRoute roles={['ADMIN']}>
              <HomePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/venues"
          element={
            <ProtectedRoute roles={['ADMIN']}>
              <VenuesPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/users"
          element={
            <ProtectedRoute roles={['ADMIN']}>
              <UsersPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/suppliers"
          element={
            <ProtectedRoute roles={['ADMIN']}>
              <SuppliersPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/tables"
          element={
            <ProtectedRoute roles={['ADMIN']}>
              <TablesPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/inventory"
          element={
            <ProtectedRoute roles={['ADMIN', 'CASHIER']}>
              <InventoryPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/room"
          element={
            <ProtectedRoute>
              <RoomPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/orders/:orderId"
          element={
            <ProtectedRoute>
              <OrderDetailPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/catalog"
          element={
            <ProtectedRoute>
              <ProductsPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/cashier"
          element={
            <ProtectedRoute roles={['CASHIER']}>
              <HomePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/waiter"
          element={
            <ProtectedRoute roles={['WAITER']}>
              <HomePage />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AuthProvider>
  )
}
