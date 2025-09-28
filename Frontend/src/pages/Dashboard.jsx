import React, {useEffect, useState} from 'react';
import '../styles.css';

import {fetchRoot} from "../APIs/EmailResponses.js";
import Calendar from "./Calendar.jsx";
import {ActionIcon, Box, Button, Fieldset, Grid, Slider, Space} from "@mantine/core";
import { IconReload } from '@tabler/icons-react';
import Notifier from "../APIs/Notifier.jsx";
import {notifications} from "@mantine/notifications";

// Configuration object - easily customizable
const CONFIG = {
  appName: "Care Inbox Control Panel",
  stats: {
    totalEmails: 12847,
    processedToday: 324,
    aiAccuracy: 98.7,
  },
  recentEmails: [
    { id: 1, subject: "Welcome to our service", recipient: "john@example.com", status: "processed", timestamp: "2 min ago" },
    { id: 2, subject: "Your order confirmation", recipient: "sarah@example.com", status: "pending", timestamp: "5 min ago" },
    { id: 3, subject: "Password reset request", recipient: "mike@example.com", status: "processed", timestamp: "8 min ago" },
    { id: 4, subject: "Newsletter subscription", recipient: "emma@example.com", status: "failed", timestamp: "12 min ago" },
    { id: 5, subject: "Thank you for your feedback", recipient: "alex@example.com", status: "processed", timestamp: "15 min ago" }
  ],
  navigation: [
    { label: 'Dashboard', icon: '📊', active: true, path: '/dashboard' },
    { label: 'Calendar', icon: '📅', active: false, path: '/calender' },
    { label: 'Email History', icon: '📧', active: false, path: '/history' },
    { label: 'AI Settings', icon: '🤖', active: false, path: '/ai-settings' },

  ]
};

function StatsCard({ title, value, subtitle, icon }) {
  return (
    <div className="stats-card glass-card fade-in-up">
      <div className="stats-header">
        <div>
          <div className="stats-label">{title}</div>
          <div className="stats-number">{value}</div>
          {subtitle && <div className="stats-subtitle">{subtitle}</div>}
        </div>
        <div className="stats-icon">{icon}</div>
      </div>
    </div>
  );
}

function RecentEmailsTable({ emails }) {
  const getStatusClass = (status) => {
    switch (status) {
      case 'processed': return 'status-processed';
      case 'pending': return 'status-pending';
      case 'failed': return 'status-failed';
      default: return '';
    }
  };

  return (
    <div className="glass-card fade-in-up">
      <div className="card-header">
        <h3>Recent Email Activity</h3>
        <button className="refresh-btn">🔄</button>
      </div>
      <div className="table-container">
        <table className="email-table">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Recipient</th>
              <th>Status</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {emails.map((email) => (
              <tr key={email.id}>
                <td className="subject-cell">{email.subject}</td>
                <td className="recipient-cell">{email.recipient}</td>
                <td>
                  <span className={`status-badge ${getStatusClass(email.status)}`}>
                    {email.status}
                  </span>
                </td>
                <td className="time-cell">{email.timestamp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Navigation({ items, onNavigate }) {
  return (
    <nav className="sidebar-nav">
      <div className="nav-header">Navigation</div>
      {items.map((item, index) => (
        <button
          key={index}
          className={`nav-item ${item.active ? 'active' : ''}`}
          onClick={() => onNavigate?.(item.path)}
        >
          <span className="nav-icon">{item.icon}</span>
          <span className="nav-label">{item.label}</span>
          <span className="nav-arrow">›</span>
        </button>
      ))}
    </nav>
  );
}

export default function Dashboard() {
  const [navItems, setNavItems] = useState(CONFIG.navigation);
  const [currentPage, setCurrentPage] = useState('/dashboard'); // Track current page
  const [localAPIResponse, setLocalAPIResponse] = useState([]);

  const handleNavigation = (path) => {
    setNavItems(items =>
        items.map(item => ({
          ...item,
          active: item.path === path
        }))
    );
    setCurrentPage(path); // update current page
    console.log('Navigating to:', path);
  };

  useEffect(() => {
    async function loadFromAPI() {
      const data = await fetchRoot();
      if (data) setLocalAPIResponse(data.Hello);
    }
    loadFromAPI();
  }, []);

    const marks = [
        { value: 0, label: 'Friendly' },
        { value: 25, label: 'Nice' },
        { value: 50, label: 'Normal' },
        { value: 75, label: 'Serious' },
        { value: 100, label: 'Corporate' },
    ];

  // Render different content based on currentPage
  const renderMainContent = () => {
    switch (currentPage) {
      case '/dashboard':
        return (
            <>
                <Grid>
                    <Grid.Col>
              <div className="welcome-section fade-in-up">
                <h2>Welcome back! 👋</h2>
                <p>Here's what's happening with your AI email system today.</p>
                <p>THIS is from your api! :) {localAPIResponse}</p>
              </div>

              {/* Stats Grid */}
              <div className="stats-grid">
                <StatsCard
                    title="Total Emails"
                    value={CONFIG.stats.totalEmails.toLocaleString()}
                    subtitle="All time processed"
                    icon="📧"
                />
                <StatsCard
                    title="Today's Activity"
                    value={CONFIG.stats.processedToday}
                    subtitle="Emails processed"
                    icon="📈"
                />
                <StatsCard
                    title="AI Accuracy"
                    value={`${CONFIG.stats.aiAccuracy}%`}
                    subtitle="Classification rate"
                    icon="🤖"
                />
              </div>
                    </Grid.Col>
                    <Grid.Col>
                        <div className="danger-box">
                            <div className="icon">
                                <span>&#x2716;</span>
                            </div>
                            <div className="content">
                                <h4>Warning</h4>
                                <p>The agent has automatically detected a high-priority message from an user.</p>
                            </div>
                        </div>
                    </Grid.Col>
                </Grid>
            </>
        );

        case '/calender':
            return (
                <div className="glass-card fade-in-up">
                    <Grid>
                        <Grid.Col span={6}>
                            <div className="welcome-section fade-in-up">
                                <h2>AI Managed Schedule</h2>
                            </div>
                        </Grid.Col>
                        <Grid.Col span={6} >
                            <ActionIcon  onClick={handleRefresh}>
                                <IconReload></IconReload>
                            </ActionIcon>
                        </Grid.Col>
                    </Grid>
                    {<Calendar key={refreshKey}/>}
                </div>
        );

      case '/history':
        return (
            <>
                <div className="welcome-section fade-in-up">
                    <h2>Email History</h2>
                </div>
                <RecentEmailsTable emails={CONFIG.recentEmails} />
            </>
        );

      case '/ai-settings':
        return (
            <Box>
                <div className="welcome-section fade-in-up">
                    <h2>AI Settings</h2>
                    <p>Configure your AI model and training settings here.</p>
                </div>
                <div>
                    <Fieldset
                        legend="Personality Adjustments"
                        style={{
                            width: "100%",         // let it expand with container
                            minWidth: 400,         // give breathing room for labels
                            padding: "3rem",       // prevent cut-off text
                            border: "1px solid rgba(255, 255, 255, 0.2)",
                            background: "var(--secondary-gradient)", // dark blue gradient
                            color: "white",                          // make text readable
                            boxShadow: "0 4px 12px rgba(0,0,0,0.3)", // soft depth
                        }}
                    >
                        <Space h="md" />
                        <Slider
                            defaultValue={50}
                            step={25}
                            marks={marks}
                            // Show value on hover
                            label={(val) => marks.find((m) => m.value === val)?.label || val}
                        />
                    </Fieldset>
                </div>
            </Box>

        );

      default:
        return <div>Page not found</div>;
    }
  };

    const [refreshKey, setRefreshKey] = useState(0);
    const handleRefresh = () => {
        setRefreshKey(prevKey => prevKey + 1); // Incrementing the key
    };

  return (
      <div className="app-shell">
        <header className="app-header">
            <Notifier />
          <div className="header-content">
            <h1 className="logo-text">{CONFIG.appName}</h1>
          </div>
        </header>
        <div className="app-body">
          <aside className="app-sidebar">
            <Navigation items={navItems} onNavigate={handleNavigation} />

            <div className="sidebar-status glass-card">
              <div className="status-icon">⚙️</div>
              <div className="status-text">System Status</div>
              <div className="status-badge status-operational">All Systems Operational</div>
            </div>
          </aside>

          <main className="app-main">
            <div className="main-content">
              {renderMainContent()}
            </div>
          </main>
        </div>
      </div>
  );
}
