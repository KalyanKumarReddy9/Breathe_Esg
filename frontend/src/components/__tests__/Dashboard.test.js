import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import Dashboard from '../Dashboard';
import api from '../api';

jest.mock('../api', () => ({
  get: jest.fn(),
  defaults: { baseURL: '/api' },
}));

test('renders dashboard with recent batches', async () => {
  api.get
    .mockResolvedValueOnce({ data: [{ id: 1, name: 'Client 1' }] })
    .mockResolvedValueOnce({
      data: [
        {
          id: 10,
          client_name: 'Client 1',
          source_type: 'SAP',
          file_name: 'sap.csv',
          status: 'COMPLETED',
          total_rows: 1,
          parsed_rows: 1,
          failed_rows: 0,
        },
      ],
    });

  const router = createMemoryRouter(
    [{ path: '/', element: <Dashboard /> }],
    {
      initialEntries: ['/'],
      future: { v7_startTransition: true, v7_relativeSplatPath: true },
    }
  );

  render(<RouterProvider router={router} />);

  expect(await screen.findByText('Dashboard Overview')).toBeInTheDocument();
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
  expect(screen.getByText('sap.csv')).toBeInTheDocument();
});
