from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import House

class HouseListView(LoginRequiredMixin, ListView):
    model = House
    template_name = 'users/house_list.html'
    context_object_name = 'houses'

class HouseDetailView(LoginRequiredMixin, DetailView):
    model = House
    template_name = 'users/house_detail.html'

class HouseCreateView(LoginRequiredMixin, CreateView):
    model = House
    template_name = 'users/house_form.html'
    fields = ['name', 'users', 'parent_houses']
    success_url = reverse_lazy('house-list')

class HouseUpdateView(LoginRequiredMixin, UpdateView):
    model = House
    template_name = 'users/house_form.html'
    fields = ['name', 'users', 'parent_houses']
    success_url = reverse_lazy('house-list')

class HouseDeleteView(LoginRequiredMixin, DeleteView):
    model = House
    template_name = 'users/house_confirm_delete.html'
    success_url = reverse_lazy('house-list')
