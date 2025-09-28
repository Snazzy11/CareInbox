import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

import { ColorSchemeToggle } from '../components/ColorSchemeToggle/ColorSchemeToggle';
import { Welcome } from '../components/Welcome/Welcome';
import Dashboard from './Dashboard.jsx'
import {Notifications} from "@mantine/notifications";
import {MantineProvider} from "@mantine/core";

export function HomePage() {
  return (
    <>
        <Dashboard />
    </>
  );
}
