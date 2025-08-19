import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { TextField, Button, Paper, Typography, Box, CircularProgress, Card, CardContent } from '@mui/material';
import { green, grey } from '@mui/material/colors';

const Chatbot = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { text: input, sender: 'user' };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post('http://127.0.0.1:8000/ask', { question: input });
      const botMessage = {
        text: response.data.answer,
        sender: 'bot'
      };
      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } catch (error) {
      const errorMessage = { text: 'Error: Could not get a response. Please check the backend server.', sender: 'bot', isError: true };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ height: '80vh', display: 'flex', flexDirection: 'column', bgcolor: 'white', border: '2px solid #616161', borderRadius: '10px' }}>
      <Box sx={{ flexGrow: 1, p: 2, overflowY: 'auto' }}>
        {messages.map((msg, index) => (
          <Box
            key={index}
            sx={{
              mb: 2,
              display: 'flex',
              justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            {msg.sender === 'bot' ? (
              <Card sx={{ maxWidth: '70%', bgcolor: grey[200] }}>
                <CardContent>
                  <Typography variant="body1">{msg.text}</Typography>
                </CardContent>
              </Card>
            ) : (
              <Paper
                elevation={0}
                sx={{
                  p: 1.5,
                  borderRadius: '10px',
                  bgcolor: green[900],
                  color: 'white',
                  maxWidth: '70%',
                  border: '1px solid #e0e0e0',
                }}
              >
                <Typography variant="body1">{msg.text}</Typography>
              </Paper>
            )}
          </Box>
        ))}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <CircularProgress />
          </Box>
        )}
      </Box>
      <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', p: 2, bgcolor: 'white', borderTop: '2px solid #616161' }}>
        <TextField
          fullWidth
          variant="standard"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          InputProps={{ disableUnderline: true }}
        />
        <Button type="submit" variant="contained" sx={{ ml: 1, bgcolor: green[900], '&:hover': { bgcolor: green[700] } }}>
          Send
        </Button>
      </Box>
    </Box>
  );
};

export default Chatbot;