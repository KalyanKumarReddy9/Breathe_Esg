import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import BatchReview from '../BatchReview';
import api from '../api';

jest.mock('../api', () => ({
  get: jest.fn(),
  post: jest.fn(),
  defaults: { baseURL: '/api' },
}));

test('renders batch review summary', async () => {
  api.get
    .mockResolvedValueOnce({
      data: {
        id: 5,
        batch_id: 5,
        source_type: 'SAP',
        status: 'COMPLETED',
        total_rows: 1,
        failed_rows: 0,
        review_summary: { pending: 1, approved: 0, flagged: 0, rejected: 0 },
        failed_records: [],
        is_exported: false,
      },
    })
    .mockResolvedValueOnce({
      data: [
        {
          id: 1,
          scope: 'SCOPE_1',
          category: 'Fuel Combustion',
          period_start: '2024-03-15',
          period_end: null,
          facility_code: 'PL01',
          quantity_value: 10,
          quantity_unit_si: 'L',
          review_status: 'PENDING',
        },
      ],
    });

  const router = createMemoryRouter(
    [{ path: '/batches/:id', element: <BatchReview /> }],
    {
      initialEntries: ['/batches/5'],
      future: { v7_startTransition: true, v7_relativeSplatPath: true },
    }
  );

  render(<RouterProvider router={router} />);

  expect(await screen.findByText(/Batch 5 Review/)).toBeInTheDocument();
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
  expect(screen.getByText('Fuel Combustion')).toBeInTheDocument();
});
