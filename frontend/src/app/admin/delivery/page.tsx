'use client'

import { useEffect, useState } from 'react'
import { admin } from '@/lib/api'
import { Plus, Edit, Trash2 } from 'lucide-react'

export default function AdminDeliveryPage() {
  const [zones, setZones] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingZone, setEditingZone] = useState<any>(null)
  const [formData, setFormData] = useState({
    city: '',
    area: '',
    charge: '',
    estimated_days: '3',
  })

  useEffect(() => {
    loadZones()
  }, [])

  const loadZones = async () => {
    try {
      const data = await admin.deliveryZones()
      setZones(data)
    } catch (error) {
      console.error('Failed to load zones:', error)
    } finally {
      setLoading(false)
    }
  }

  const openCreateModal = () => {
    setEditingZone(null)
    setFormData({ city: '', area: '', charge: '', estimated_days: '3' })
    setShowModal(true)
  }

  const openEditModal = (zone: any) => {
    setEditingZone(zone)
    setFormData({
      city: zone.city,
      area: zone.area || '',
      charge: zone.charge.toString(),
      estimated_days: zone.estimated_days.toString(),
    })
    setShowModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const data = {
        city: formData.city,
        area: formData.area || undefined,
        charge: Number(formData.charge),
        estimated_days: Number(formData.estimated_days),
      }

      if (editingZone) {
        await admin.updateDeliveryZone(editingZone.id, data)
      } else {
        await admin.createDeliveryZone(data)
      }
      setShowModal(false)
      loadZones()
    } catch (error: any) {
      alert(error.message || 'Failed to save zone')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this zone?')) return
    try {
      await admin.deleteDeliveryZone(id)
      setZones(prev => prev.filter(z => z.id !== id))
    } catch (error: any) {
      alert(error.message || 'Failed to delete zone')
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Delivery Zones</h1>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
        >
          <Plus className="w-4 h-4" />
          Add Zone
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : zones.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No delivery zones found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b text-left text-sm text-gray-600">
                  <th className="p-4 font-medium">City</th>
                  <th className="p-4 font-medium">Area</th>
                  <th className="p-4 font-medium">Fee</th>
                  <th className="p-4 font-medium">Days</th>
                  <th className="p-4 font-medium">Status</th>
                  <th className="p-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {zones.map((zone) => (
                  <tr key={zone.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="p-4 font-medium">{zone.city}</td>
                    <td className="p-4 text-gray-600">{zone.area || '-'}</td>
                    <td className="p-4">৳{zone.charge.toLocaleString()}</td>
                    <td className="p-4">{zone.estimated_days} days</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        zone.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {zone.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => openEditModal(zone)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(zone.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold">
                {editingZone ? 'Edit Zone' : 'Add Zone'}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-gray-700">
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">City *</label>
                <input
                  type="text"
                  required
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Dhaka"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Area</label>
                <input
                  type="text"
                  value={formData.area}
                  onChange={(e) => setFormData({ ...formData, area: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="e.g., Dhanmondi (optional)"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Fee (৳) *</label>
                  <input
                    type="number"
                    required
                    value={formData.charge}
                    onChange={(e) => setFormData({ ...formData, charge: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Days *</label>
                  <input
                    type="number"
                    required
                    value={formData.estimated_days}
                    onChange={(e) => setFormData({ ...formData, estimated_days: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
              <div className="flex gap-4 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  {editingZone ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
