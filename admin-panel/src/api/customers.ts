import { api, unwrap } from "./client";
import type { components } from "./schema";

export type Customer = components["schemas"]["Customer"];
export type CustomerStatus = components["schemas"]["CustomerStatusEnum"];
export type CustomerPage = components["schemas"]["PaginatedCustomerList"];

export type CustomerQuery = { search: string; status: CustomerStatus | ""; page: number };

export const PAGE_SIZE = 20;

export const customersService = {
  list({ search, status, page }: CustomerQuery): Promise<CustomerPage> {
    return unwrap(
      api.GET("/api/v1/admin/customers/", {
        params: { query: { search: search || undefined, status: status || undefined, page } },
      }),
    );
  },

  block(id: number): Promise<Customer> {
    return unwrap(api.POST("/api/v1/admin/customers/{id}/block/", { params: { path: { id } } }));
  },

  unblock(id: number): Promise<Customer> {
    return unwrap(api.POST("/api/v1/admin/customers/{id}/unblock/", { params: { path: { id } } }));
  },

  remove(id: number): Promise<Customer> {
    return unwrap(api.POST("/api/v1/admin/customers/{id}/delete/", { params: { path: { id } } }));
  },
};
