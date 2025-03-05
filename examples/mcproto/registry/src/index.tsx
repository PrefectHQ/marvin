import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './components/App';
import './styles/styles.css';

const container = document.getElementById('root');
if (!container) throw new Error('Failed to find root element');
const root = createRoot(container);
root.render(<App />); 