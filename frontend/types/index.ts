export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  salary_range?: string;
  description: string;
  requirements: string[];
  posted_at: string;
  platform: 'linkedin' | 'indeed' | 'glassdoor';
  match_score?: number; // AI evaluation
}

export interface Application {
  id: number;
  job_id: number;
  user_id: string;
  status: 'PENDING' | 'APPLIED' | 'INTERVIEW' | 'REJECTED' | 'OFFER';
  applied_at: string;
  resume_version: string;
  notes?: string;
}

export interface UserProfile {
  id: string;
  email: string;
  linkedin_connected: boolean;
  resume_url?: string;
  credits: number;
}



// [Building a Job Dashboard in React](https://www.youtube.com/watch?v=k4l3XJq8T6o)

// This video is relevant because it demonstrates building a responsive job dashboard with charts and filters, similar to your LoopCV-style requirement.
