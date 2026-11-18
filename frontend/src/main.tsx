import './safe-load.css';
import './booking-pilot.css';
import ManufacturerSupportWindow from './features/portal/ManufacturerSupportWindow';
import {WorkspaceProvider} from './context/WorkspaceContext';
import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import App from './App';
import {AuthProvider} from './context/AuthContext';
import './styles.css';
import './dark.css';
import './preferences.css';
import './operational.css';
import './muse.css';
import {PreferencesProvider} from './context/PreferencesContext';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><ManufacturerSupportWindow><BrowserRouter><AuthProvider><WorkspaceProvider><PreferencesProvider><App/></PreferencesProvider></WorkspaceProvider></AuthProvider></BrowserRouter></ManufacturerSupportWindow></React.StrictMode>);

import './login-cinematic.css';
