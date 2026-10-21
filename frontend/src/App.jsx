import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider } from './context/AuthContext'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import BillingPage from './pages/BillingPage'
import CashierPage from './pages/CashierPage'
import InventoryPage from './pages/InventoryPage'
import InvoicePage from './pages/InvoicePage'
import OrderDetailPage from './pages/OrderDetailPage'
import ProductsPage from './pages/ProductsPage'
import ReportsPage from './pages/ReportsPage'
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
          path="/cashier/orders"
          element={
            <ProtectedRoute roles={['CASHIER', 'ADMIN']}>
              <CashierPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/reports"
          element={
            <ProtectedRoute roles={['ADMIN', 'CASHIER']}>
              <ReportsPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/billing"
          element={
            <ProtectedRoute roles={['CASHIER', 'ADMIN']}>
              <BillingPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/billing/invoices/:invoiceId"
          element={
            <ProtectedRoute roles={['CASHIER', 'ADMIN']}>
              <InvoicePage />
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
