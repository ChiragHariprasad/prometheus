import api from './api';
import { Customer, CustomerEvent } from '../types';

export const customersService = {
  listCustomers: async (params?: { page?: number; page_size?: number; search?: string }) => {
    const res = await api.get('/customers', { params });
    return res.data; // Expected response: { data: Customer[], total: number, page: number, page_size: number }
  },

  createCustomer: async (data: Partial<Customer>) => {
    const res = await api.post('/customers', data);
    return res.data;
  },

  batchCreateCustomers: async (data: { customers: Array<Partial<Customer>> }) => {
    const res = await api.post('/customers/batch', data);
    return res.data;
  },

  searchCustomers: async (query: string) => {
    const res = await api.get('/customers/search', { params: { query } });
    return res.data; // Expected response: Customer[]
  },

  deleteCustomer: async (customerId: string) => {
    const res = await api.delete(`/customers/${customerId}`);
    return res.data;
  },

  getCustomer: async (customerId: string) => {
    const res = await api.get(`/customers/${customerId}`);
    return res.data; // Expected response: Customer
  },

  updateCustomer: async (customerId: string, data: Partial<Customer>) => {
    const res = await api.put(`/customers/${customerId}`, data);
    return res.data;
  },

  getCustomerEvents: async (customerId: string, params?: { page?: number; page_size?: number }) => {
    const res = await api.get(`/customers/${customerId}/events`, { params });
    return res.data; // Expected response: { data: CustomerEvent[], total: number }
  },

  getCustomerInterests: async (customerId: string) => {
    const res = await api.get(`/customers/${customerId}/interests`);
    return res.data; // Expected: string[]
  },

  mergeCustomers: async (data: { primary_id: string; secondary_id: string }) => {
    const res = await api.post('/customers/merge', data);
    return res.data;
  },

  getCustomerPreferences: async (customerId: string) => {
    const res = await api.get(`/customers/${customerId}/preferences`);
    return res.data;
  },

  updateCustomerPreferences: async (customerId: string, data: Record<string, any>) => {
    const res = await api.put(`/customers/${customerId}/preferences`, data);
    return res.data;
  },

  getCustomerProfile: async (customerId: string) => {
    const res = await api.get(`/customers/${customerId}/profile`);
    return res.data;
  },

  getCustomerSegments: async (customerId: string) => {
    const res = await api.get(`/customers/${customerId}/segments`);
    return res.data; // Expected: string[]
  },
};
