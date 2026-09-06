export type ComplaintSource = 'citizen' | 'iot_predicted' | 'iot_detected';

export interface Complaint {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'resolved';
  source: ComplaintSource;
  createdAt: string;
  zoneId?: string;
}
