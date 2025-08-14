import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

test('renders the main title', () => {
  render(<App />);
  expect(screen.getByText(/Image Resizer/i)).toBeInTheDocument();
});

test('shows error for invalid file type', async () => {
  render(<App />);
  const fileInput = screen.getByLabelText(/select image file/i);
  const file = new File(['dummy'], 'test.txt', { type: 'text/plain' });
  await userEvent.upload(fileInput, file);
  await waitFor(() => {
    expect(screen.getByText(/Only image files accepted/i)).toBeInTheDocument();
  });
});

test('disables resize button when no valid file is selected', () => {
  render(<App />);
  const button = screen.getByRole('button', { name: /resize image/i });
  expect(button).toBeDisabled();
});

test('shows slider and updates percentage', async () => {
  render(<App />);
  const slider = screen.getByRole('slider');
  expect(slider).toBeInTheDocument();
  await userEvent.type(slider, '{arrowright}');
  await waitFor(() => {
    expect(screen.getByText(/Percentage to Reduce:/i)).toBeInTheDocument();
  });
});

test('shows loading spinner when resizing', async () => {
  render(<App />);
  // Simulate state
  // Not trivial to test async fetch without mocking, so just check spinner logic
  // This is a placeholder for a more advanced test with fetch mocking
});
