import { useState } from 'react'
import { 
  Container, 
  TextField, 
  Button, 
  Paper, 
  Typography, 
  Box,
  CircularProgress
} from '@mui/material'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker'
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import axios from 'axios'

// Configure dayjs to handle timezones
dayjs.extend(utc)
dayjs.extend(timezone)

function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [eventDetails, setEventDetails] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async () => {
    setLoading(true)
    setError(null)
    setEventDetails(null)
    
    try {
      const response = await axios.post('/parse-event', { url })
      
      if (response.status === 200) {
        const data = response.data
        // Convert ISO strings to dayjs objects for the date pickers
        setEventDetails({
          ...data,
          start_time: data.start_time ? dayjs(data.start_time) : null,
          end_time: data.end_time ? dayjs(data.end_time) : null
        })
      } else if (response.status === 422 && response.data.parsed_details) {
        const data = response.data.parsed_details
        setEventDetails({
          ...data,
          start_time: data.start_time ? dayjs(data.start_time) : null,
          end_time: data.end_time ? dayjs(data.end_time) : null
        })
        setError({
          message: 'Event details were parsed but have some issues:',
          issues: response.data.issues
        })
      }
    } catch (err) {
      console.error('Error parsing event:', err.response || err)
      
      const errorResponse = err.response?.data
      if (errorResponse) {
        setError({
          message: errorResponse.error,
          issues: errorResponse.issues || [errorResponse.details],
          raw: errorResponse.raw_response
        })
      } else {
        setError({
          message: 'Failed to parse event',
          issues: [err.message]
        })
      }
    }
    setLoading(false)
  }

  const handleCreateEvent = async () => {
    setLoading(true)
    setError(null)
    try {
      // Convert dayjs objects back to ISO strings for the API
      const eventToSend = {
        ...eventDetails,
        start_time: eventDetails.start_time?.toISOString(),
        end_time: eventDetails.end_time?.toISOString()
      }
      
      const response = await axios.post('/create-event', eventToSend)
      alert('Event created successfully!')
    } catch (err) {
      console.error('Error creating event:', err.response || err)
      const errorResponse = err.response?.data
      setError({
        message: 'Failed to create event',
        issues: errorResponse?.issues || [errorResponse?.details || err.message]
      })
    }
    setLoading(false)
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Event Parser
        </Typography>
        
        <Paper sx={{ p: 3, mb: 3 }}>
          <TextField
            fullWidth
            label="Event Page URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Button 
            variant="contained" 
            onClick={handleSubmit}
            disabled={loading || !url}
          >
            {loading ? <CircularProgress size={24} /> : 'Parse Event'}
          </Button>
        </Paper>

        {error && (
          <Paper sx={{ p: 3, mb: 3, bgcolor: 'error.light' }}>
            <Typography variant="h6" color="error.contrastText" gutterBottom>
              {error.message}
            </Typography>
            {error.issues && error.issues.length > 0 && (
              <Box component="ul" sx={{ color: 'error.contrastText', mt: 1 }}>
                {error.issues.map((issue, index) => (
                  <li key={index}>{issue}</li>
                ))}
              </Box>
            )}
            {error.raw && (
              <Box sx={{ mt: 2 }}>
                <Typography color="error.contrastText" variant="subtitle2">
                  Raw AI Response:
                </Typography>
                <Box 
                  component="pre"
                  sx={{ 
                    mt: 1,
                    p: 2,
                    bgcolor: 'rgba(0,0,0,0.1)',
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: 200,
                    color: 'error.contrastText'
                  }}
                >
                  {error.raw}
                </Box>
              </Box>
            )}
          </Paper>
        )}

        {eventDetails && (
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Event Details
            </Typography>
            
            <LocalizationProvider dateAdapter={AdapterDayjs}>
              <TextField
                fullWidth
                label="Title"
                value={eventDetails.title || ''}
                onChange={(e) => setEventDetails({...eventDetails, title: e.target.value})}
                sx={{ mb: 2 }}
                error={error?.issues?.includes('Missing required field: title')}
              />
              
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Description"
                value={eventDetails.description || ''}
                onChange={(e) => setEventDetails({...eventDetails, description: e.target.value})}
                sx={{ mb: 2 }}
                error={error?.issues?.includes('Missing required field: description')}
              />
              
              <DateTimePicker
                label="Start Time"
                value={eventDetails.start_time}
                onChange={(newValue) => setEventDetails({...eventDetails, start_time: newValue})}
                sx={{ mb: 2, width: '100%' }}
                slotProps={{
                  textField: {
                    error: error?.issues?.some(issue => issue.includes('start_time'))
                  }
                }}
              />
              
              <DateTimePicker
                label="End Time"
                value={eventDetails.end_time}
                onChange={(newValue) => setEventDetails({...eventDetails, end_time: newValue})}
                sx={{ mb: 2, width: '100%' }}
                slotProps={{
                  textField: {
                    error: error?.issues?.some(issue => issue.includes('end_time'))
                  }
                }}
              />
              
              <TextField
                fullWidth
                label="Location"
                value={eventDetails.location || ''}
                onChange={(e) => setEventDetails({...eventDetails, location: e.target.value})}
                sx={{ mb: 2 }}
                error={error?.issues?.includes('Missing required field: location')}
              />
              
              <Button 
                variant="contained" 
                onClick={handleCreateEvent}
                disabled={loading || (error && !eventDetails)}
                sx={{ mt: 2 }}
              >
                {loading ? <CircularProgress size={24} /> : 'Create Event'}
              </Button>
            </LocalizationProvider>
          </Paper>
        )}
      </Box>
    </Container>
  )
}

export default App
