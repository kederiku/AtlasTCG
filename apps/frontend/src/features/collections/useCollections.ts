import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getJobs, requestCollection, requestImageRepair } from "./api";
import type { Job } from "./types";

export function useCollections() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [collect, setCollect] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: getJobs,
    refetchInterval: 2000,
  });
  const mutation = useMutation({
    mutationFn: requestCollection,
    onSuccess: () => {
      setCollect(false);
      navigate("/collections");
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const active =
    jobs.data?.filter((job) => ["queued", "running"].includes(job.status))
      .length || 0;
  const repairMutation = useMutation({
    mutationFn: requestImageRepair,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const openForm = () => {
    mutation.reset();
    setCollect(true);
  };
  return {
    jobs,
    active,
    collect,
    setCollect,
    selectedJob,
    setSelectedJob,
    mutation,
    repairMutation,
    openForm,
  };
}
