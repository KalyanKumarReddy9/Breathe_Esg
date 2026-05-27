import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import Upload from '../Upload';
import api from '../api';

jest.mock('../api', () => ({
  get: jest.fn(),
  post: jest.fn(),
  defaults: { baseURL: '/api' },
}));

test('loads clients and renders upload form', async () => {
  api.get.mockResolvedValueOnce({ data: [{ id: 1, name: 'Client 1' }] });

  const router = createMemoryRouter(
    [{ path: '/', element: <Upload /> }],
    {
      initialEntries: ['/'],
      future: { v7_startTransition: true, v7_relativeSplatPath: true },
    }
  );

  render(<RouterProvider router={router} />);

  expect(await screen.findByText('Upload Emissions Data')).toBeInTheDocument();
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(1));
  expect(screen.getByLabelText('Client')).toBeInTheDocument();
});
